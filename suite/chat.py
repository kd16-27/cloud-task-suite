"""Small retrieval model: TF-IDF cosine similarity over curated training patterns."""
import math
import re
from collections import Counter

FAQ = [
     {
        'id': 'avdisplay',
        'title': 'AV display basic checks',
        'patterns': [
            'My conference room display has no picture',
            'The meeting room screen is blank',
            'How do I troubleshoot no video on a display?'
        ],
        'answer': 'Start by checking that the display is powered on and the correct input is selected. Confirm the source device is awake and its video cable is connected. If there is still no picture, record the symptoms and contact your AV support team.'
    },
    {'id': 'booking', 'title': 'Book a demonstration pass',
     'patterns': ['How do I book a bus pass?', 'Reserve a bus ticket', 'Buy a pass for a route'],
     'answer': 'Sign in, open Bus passes, choose a route, and select Book pass. This demo issues a pass without charging a payment card.'},
    {'id': 'recover', 'title': 'Recover a lost pass',
     'patterns': ['I lost my bus ticket', 'Where can I find my pass again?', 'Recover a missing booking'],
     'answer': 'Sign in to the account that booked the pass and select My passes. The database keeps your booking; a screenshot is not your only copy.'},
    {'id': 'cancel', 'title': 'Cancel a booking',
     'patterns': ['How do I cancel my booking?', 'Cancel a bus pass', 'Return my ticket and free a seat'],
     'answer': 'Open My passes and select Cancel on an active pass. The cancellation releases its seat once. This demo does not process payments or refunds.'},
    {'id': 'pricing', 'title': 'Server controlled fares',
     'patterns': ['How is the ticket price calculated?', 'Can I change the fare?', 'Who sets bus pricing?'],
     'answer': 'The server reads the fare from the route database. A price supplied by a browser request is rejected.'},
    {'id': 'duplicate', 'title': 'Record deduplication',
     'patterns': ['Why was my duplicate record rejected?', 'How do you detect redundant data?', 'Prevent duplicate records'],
     'answer': 'Each account has unique source IDs and normalized name-and-email content. Repeated content is redundant even with a new ID; changed content under an existing ID is a conflict. Matching names alone require review.'},
    {'id': 'falsepositive', 'title': 'Avoid merging different people',
     'patterns': ['What is a false positive duplicate?', 'Two different people have the same name', 'Confirm distinct records after review'],
     'answer': 'A shared name does not prove a duplicate. Compare the source IDs and details, then confirm a genuinely distinct record. Validation here checks structure; it does not prove a real identity.'},
    {'id': 'encryption', 'title': 'Sensitive field encryption',
     'patterns': ['How is sensitive information encrypted?', 'Do you use AES encryption?', 'Is vault data protected?'],
     'answer': 'Vault contents use AES-256-GCM with a new random nonce for each encryption. The key comes from server configuration. Passwords use scrypt hashing instead of reversible encryption.'},
    {'id': 'sql', 'title': 'SQL injection defenses',
     'patterns': ['How do you stop SQL injection?', 'What are parameterized SQL queries?', 'Prevent database injection attacks'],
     'answer': 'Database statements use bound parameters. Scoped bearer tokens and owner checks restrict access. Suspicious input is logged as an indicator, not accepted as executable SQL.'},
    {'id': 'token', 'title': 'Capability token access',
     'patterns': ['What is a capability token?', 'Why did my token expire?', 'How do access permissions work?'],
     'answer': 'Login issues a short-lived bearer token with allowed actions. Only a hash is stored in the database. Sign out revokes it; sharing a token shares its access until expiry or revocation.'},
    {'id': 'cloud', 'title': 'Cloud deployment architecture',
     'patterns': ['How does the cloud application scale?', 'Explain autoscaling and reliability', 'Where will the cloud database run?'],
     'answer': 'The included AWS template uses an HTTPS load balancer, ECS Fargate application tasks, and a private PostgreSQL RDS database. CPU target tracking adjusts task count. Live deployment and scaling evidence must be collected separately.'}
]
STOP = set('a an the is are do does i my you your how what to of and in for can it'.split())

def words(text):
    return [t for t in re.findall(r'[a-z0-9]+', text.lower()) if t not in STOP]

class Retriever:
    def __init__(self):
        self.docs = [(f, words(p)) for f in FAQ for p in f['patterns']]
        df = Counter(t for _, doc in self.docs for t in set(doc))
        self.idf = {t: math.log((1 + len(self.docs)) / (1 + n)) + 1 for t, n in df.items()}
        self.vectors = [self.vector(doc) for _, doc in self.docs]

    def vector(self, tokens):
        counts = Counter(tokens)
        vec = {t: n * self.idf[t] for t, n in counts.items() if t in self.idf}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1
        return {t: v / norm for t, v in vec.items()}

    def answer(self, question):
        query_words = words(question)
        coverage = sum(t in self.idf for t in query_words) / max(1, len(query_words))
        q = self.vector(query_words)
        by_intent = {}
        for (faq, _), vec in zip(self.docs, self.vectors):
            score = sum(v * vec.get(t, 0) for t, v in q.items())
            if score > by_intent.get(faq['id'], (0, None))[0]:
                by_intent[faq['id']] = (score, faq)
        ranked = sorted(by_intent.values(), key=lambda x: x[0], reverse=True)
        if coverage < .5 or not ranked or ranked[0][0] < .30 or (len(ranked) > 1 and ranked[0][0] - ranked[1][0] < .06):
            return {'matched': False, 'answer': 'I do not have a reliable answer in my training notes. Ask about booking, lost passes, cancellations, pricing, duplicate records, encryption, SQL injection, access tokens, or cloud deployment.', 'source': None, 'similarity': round(ranked[0][0], 3) if ranked else 0}
        score, faq = ranked[0]
        return {'matched': True, 'answer': faq['answer'], 'source': faq['title'],
                'intent': faq['id'], 'similarity': round(score, 3)}
