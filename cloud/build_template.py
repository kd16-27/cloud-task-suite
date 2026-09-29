"""Generate the reviewable CloudFormation JSON. No AWS calls are made."""
import json
from pathlib import Path
R={}
def ref(x):return {'Ref':x}
def get(x,y):return {'Fn::GetAtt':[x,y]}
def sub(x):return {'Fn::Sub':x}
def resource(name,kind,props,**extra):R[name]={'Type':kind,'Properties':props,**extra}
def env(name,value):return {'Name':name,'Value':value}
def secret(name,value):return {'Name':name,'ValueFrom':value}
resource('Vpc','AWS::EC2::VPC',{'CidrBlock':'10.42.0.0/16','EnableDnsSupport':True,'EnableDnsHostnames':True})
resource('Gateway','AWS::EC2::InternetGateway',{})
resource('AttachGateway','AWS::EC2::VPCGatewayAttachment',{'VpcId':ref('Vpc'),'InternetGatewayId':ref('Gateway')})
resource('PublicRouteTable','AWS::EC2::RouteTable',{'VpcId':ref('Vpc')})
resource('DefaultRoute','AWS::EC2::Route',{'RouteTableId':ref('PublicRouteTable'),'DestinationCidrBlock':'0.0.0.0/0','GatewayId':ref('Gateway')},DependsOn='AttachGateway')
for n,zone in [('A',0),('B',1)]:
    az={'Fn::Select':[zone,{'Fn::GetAZs':''}]}
    for kind,base in [('Public',1),('Private',11)]:
        name=kind+'Subnet'+n
        resource(name,'AWS::EC2::Subnet',{'VpcId':ref('Vpc'),'CidrBlock':f'10.42.{base+zone}.0/24','AvailabilityZone':az,'MapPublicIpOnLaunch':kind=='Public'})
        if kind=='Public':resource('RouteAssociation'+n,'AWS::EC2::SubnetRouteTableAssociation',{'SubnetId':ref(name),'RouteTableId':ref('PublicRouteTable')})
resource('AlbSecurity','AWS::EC2::SecurityGroup',{'VpcId':ref('Vpc'),'GroupDescription':'HTTPS public entry; HTTP redirects', 'SecurityGroupIngress':[{'IpProtocol':'tcp','FromPort':p,'ToPort':p,'CidrIp':'0.0.0.0/0'} for p in [80,443]]})
resource('AppSecurity','AWS::EC2::SecurityGroup',{'VpcId':ref('Vpc'),'GroupDescription':'Only load balancer can reach application','SecurityGroupIngress':[{'IpProtocol':'tcp','FromPort':8080,'ToPort':8080,'SourceSecurityGroupId':ref('AlbSecurity')}]})
resource('DbSecurity','AWS::EC2::SecurityGroup',{'VpcId':ref('Vpc'),'GroupDescription':'Only application tasks can reach PostgreSQL','SecurityGroupIngress':[{'IpProtocol':'tcp','FromPort':5432,'ToPort':5432,'SourceSecurityGroupId':ref('AppSecurity')}]})
resource('DbSubnets','AWS::RDS::DBSubnetGroup',{'DBSubnetGroupDescription':'Isolated database subnets','SubnetIds':[ref('PrivateSubnetA'),ref('PrivateSubnetB')]})
resource('Database','AWS::RDS::DBInstance',{'Engine':'postgres','DBInstanceClass':'db.t4g.micro','AllocatedStorage':'20','MaxAllocatedStorage':100,'StorageEncrypted':True,'StorageType':'gp3','DBName':'cloudlab','MasterUsername':'labadmin','ManageMasterUserPassword':True,'DBSubnetGroupName':ref('DbSubnets'),'VPCSecurityGroups':[ref('DbSecurity')],'PubliclyAccessible':False,'MultiAZ':{'Fn::Equals':[ref('DatabaseMultiAZ'),'true']},'BackupRetentionPeriod':7,'AutoMinorVersionUpgrade':True},DeletionPolicy='Snapshot',UpdateReplacePolicy='Snapshot')
resource('AppDbSecret','AWS::SecretsManager::Secret',{'Description':'Restricted application database password','GenerateSecretString':{'SecretStringTemplate':'{"username":"labapp"}','GenerateStringKey':'password','PasswordLength':40,'ExcludePunctuation':True}})
resource('EncryptionSecret','AWS::SecretsManager::Secret',{'Description':'High entropy encryption and pass signing root secret','GenerateSecretString':{'PasswordLength':64,'ExcludePunctuation':True}},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
resource('AdminSecret','AWS::SecretsManager::Secret',{'Description':'Initial demonstration administrator password','GenerateSecretString':{'PasswordLength':32,'ExcludePunctuation':True}})
assume={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'ecs-tasks.amazonaws.com'},'Action':'sts:AssumeRole'}]}
resource('ExecutionRole','AWS::IAM::Role',{'AssumeRolePolicyDocument':assume,'ManagedPolicyArns':[sub('arn:${AWS::Partition}:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy')],'Policies':[{'PolicyName':'ReadTaskSecrets','PolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['secretsmanager:GetSecretValue'],'Resource':[get('Database','MasterUserSecret.SecretArn'),ref('AppDbSecret'),ref('EncryptionSecret'),ref('AdminSecret')]}]}}]})
resource('TaskRole','AWS::IAM::Role',{'AssumeRolePolicyDocument':assume})
resource('Logs','AWS::Logs::LogGroup',{'RetentionInDays':7})
resource('Cluster','AWS::ECS::Cluster',{'ClusterSettings':[{'Name':'containerInsights','Value':'enabled'}]})
log={'LogDriver':'awslogs','Options':{'awslogs-group':ref('Logs'),'awslogs-region':ref('AWS::Region'),'awslogs-stream-prefix':'cloudlab'}}
common=[env('DB_HOST',get('Database','Endpoint.Address')),env('DB_NAME','cloudlab'),env('DB_SSLROOTCERT','/app/cloud/global-bundle.pem')]
admin_password={'Fn::Join':['',[get('Database','MasterUserSecret.SecretArn'),':password::']]}
app_password=sub('${AppDbSecret}:password::')
resource('TaskDefinition','AWS::ECS::TaskDefinition',{'Cpu':'512','Memory':'1024','NetworkMode':'awsvpc','RequiresCompatibilities':['FARGATE'],'ExecutionRoleArn':get('ExecutionRole','Arn'),'TaskRoleArn':get('TaskRole','Arn'),'RuntimePlatform':{'CpuArchitecture':'X86_64','OperatingSystemFamily':'LINUX'},'ContainerDefinitions':[
 {'Name':'initialize','Image':ref('ImageUri'),'Essential':False,'Command':['python','-m','suite.init_cloud'],'Environment':common+[env('DB_USER','labadmin'),env('ADMIN_EMAIL',ref('AdminEmail'))],'Secrets':[secret('DB_PASSWORD',admin_password),secret('APP_DB_PASSWORD',app_password),secret('ADMIN_PASSWORD',ref('AdminSecret'))],'LogConfiguration':log},
 {'Name':'web','Image':ref('ImageUri'),'Essential':True,'DependsOn':[{'ContainerName':'initialize','Condition':'SUCCESS'}],'PortMappings':[{'ContainerPort':8080,'Protocol':'tcp'}],'Environment':common+[env('DB_USER','labapp'),env('AUTO_INIT','false'),env('TRUST_PROXY','true'),env('APP_HOST','0.0.0.0')],'Secrets':[secret('DB_PASSWORD',app_password),secret('ENCRYPTION_SECRET',ref('EncryptionSecret'))],'LogConfiguration':log}
]})
resource('LoadBalancer','AWS::ElasticLoadBalancingV2::LoadBalancer',{'Scheme':'internet-facing','Type':'application','Subnets':[ref('PublicSubnetA'),ref('PublicSubnetB')],'SecurityGroups':[ref('AlbSecurity')]})
resource('TargetGroup','AWS::ElasticLoadBalancingV2::TargetGroup',{'VpcId':ref('Vpc'),'Port':8080,'Protocol':'HTTP','TargetType':'ip','HealthCheckPath':'/health','HealthCheckIntervalSeconds':30,'HealthyThresholdCount':2,'UnhealthyThresholdCount':3,'TargetGroupAttributes':[{'Key':'deregistration_delay.timeout_seconds','Value':'30'}]})
resource('HttpsListener','AWS::ElasticLoadBalancingV2::Listener',{'LoadBalancerArn':ref('LoadBalancer'),'Port':443,'Protocol':'HTTPS','Certificates':[{'CertificateArn':ref('CertificateArn')}],'SslPolicy':'ELBSecurityPolicy-TLS13-1-2-2021-06','DefaultActions':[{'Type':'forward','TargetGroupArn':ref('TargetGroup')}]})
resource('HttpListener','AWS::ElasticLoadBalancingV2::Listener',{'LoadBalancerArn':ref('LoadBalancer'),'Port':80,'Protocol':'HTTP','DefaultActions':[{'Type':'redirect','RedirectConfig':{'Protocol':'HTTPS','Port':'443','StatusCode':'HTTP_301'}}]})
resource('Service','AWS::ECS::Service',{'Cluster':ref('Cluster'),'TaskDefinition':ref('TaskDefinition'),'DesiredCount':2,'LaunchType':'FARGATE','PlatformVersion':'LATEST','HealthCheckGracePeriodSeconds':180,'DeploymentConfiguration':{'DeploymentCircuitBreaker':{'Enable':True,'Rollback':True},'MinimumHealthyPercent':100,'MaximumPercent':200},'NetworkConfiguration':{'AwsvpcConfiguration':{'AssignPublicIp':'ENABLED','Subnets':[ref('PublicSubnetA'),ref('PublicSubnetB')],'SecurityGroups':[ref('AppSecurity')]}},'LoadBalancers':[{'TargetGroupArn':ref('TargetGroup'),'ContainerName':'web','ContainerPort':8080}]},DependsOn=['HttpsListener','DefaultRoute'])
resource('ScalingRole','AWS::IAM::Role',{'AssumeRolePolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'application-autoscaling.amazonaws.com'},'Action':'sts:AssumeRole'}]},'Policies':[{'PolicyName':'ScaleEcsService','PolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['ecs:DescribeServices','ecs:UpdateService'],'Resource':get('Service','ServiceArn')},{'Effect':'Allow','Action':['cloudwatch:PutMetricAlarm','cloudwatch:DescribeAlarms','cloudwatch:DeleteAlarms'],'Resource':'*'}]}}]})
resource('ScalableTarget','AWS::ApplicationAutoScaling::ScalableTarget',{'MinCapacity':2,'MaxCapacity':4,'ResourceId':sub('service/${Cluster}/${Service.Name}'),'RoleARN':get('ScalingRole','Arn'),'ScalableDimension':'ecs:service:DesiredCount','ServiceNamespace':'ecs'})
resource('CpuScaling','AWS::ApplicationAutoScaling::ScalingPolicy',{'PolicyName':'CloudLabCpuTarget','PolicyType':'TargetTrackingScaling','ScalingTargetId':ref('ScalableTarget'),'TargetTrackingScalingPolicyConfiguration':{'TargetValue':60.0,'ScaleInCooldown':120,'ScaleOutCooldown':60,'PredefinedMetricSpecification':{'PredefinedMetricType':'ECSServiceAverageCPUUtilization'}}})
# CloudFormation cannot use a raw Fn::Equals in a resource property; map a string parameter to bool.
R['Database']['Properties']['MultiAZ']={'Fn::If':['UseMultiAZ',True,False]}
T={'AWSTemplateFormatVersion':'2010-09-09','Description':'Cloud Task Lab — Fargate autoscaling + encrypted private PostgreSQL + HTTPS. Creates billable resources.',
 'Parameters':{'ImageUri':{'Type':'String','Description':'ECR image URI ending in an immutable digest or reviewed tag'},'CertificateArn':{'Type':'String','Description':'Issued ACM certificate ARN in this region for DomainName'},'DomainName':{'Type':'String','Description':'Owned hostname, e.g. lab.example.com'},'AdminEmail':{'Type':'String','Description':'Initial demo admin email; use fictional data'},'DatabaseMultiAZ':{'Type':'String','AllowedValues':['true','false'],'Default':'false','Description':'Enable for database failover; increases charges'}},
 'Conditions':{'UseMultiAZ':{'Fn::Equals':[ref('DatabaseMultiAZ'),'true']}},'Resources':R,
 'Outputs':{'AppUrl':{'Value':sub('https://${DomainName}')},'LoadBalancerDns':{'Value':get('LoadBalancer','DNSName')},'ClusterName':{'Value':ref('Cluster')},'ServiceName':{'Value':get('Service','Name')},'AdminPasswordSecretArn':{'Value':ref('AdminSecret')},'EncryptionSecretArn':{'Value':ref('EncryptionSecret')},'DatabaseIdentifier':{'Value':ref('Database')}}}
Path(__file__).with_name('cloudformation.json').write_text(json.dumps(T,indent=2)+'\n')
print('Generated cloud/cloudformation.json')
