from troposphere import Output, Ref, Template, GetAtt, Parameter
from troposphere.s3 import Bucket, Private, NotificationConfiguration, LambdaConfigurations, Filter, Rules, S3Key
from troposphere.sns import Topic, Subscription
from troposphere.awslambda import MAXIMUM_MEMORY, MINIMUM_MEMORY, Code, Function, Permission, Environment, EventInvokeConfig, EventSourceMapping
from troposphere.constants import NUMBER, STRING
from troposphere.iam import Policy, Role
from troposphere.sqs import Queue
import yaml

t = Template()

t.set_version("2010-09-09")
t.set_description(
    "Cloud Formation template to define all AWS resources required in the project deployment"
)

MemorySize = t.add_parameter(
    Parameter(
        "LambdaMemorySize",
        Type=NUMBER,
        Description="Memory allocated to the Lambda Function",
        Default="500",
        MinValue=MINIMUM_MEMORY,
        MaxValue=MAXIMUM_MEMORY,
    )
)

Timeout = t.add_parameter(
    Parameter(
        "LambdaTimeout",
        Type=NUMBER,
        Description="Lambda function timeout",
        Default="360",
    )
)

Landings3Bucket = t.add_parameter(
    Parameter(
        "Landings3Bucket",
        Type=STRING,
        Description="Landing bucket for the incoming file",
        Default="landing-hit-level-data",
    )
)

Intermediates3Bucket = t.add_parameter(
    Parameter(
        "Intermediates3Bucket",
        Type=STRING,
        Description="Intermediate bucket landing DQ completed and split files",
        Default="intermediate-hit-level-data",
    )
)

Processeds3Bucket = t.add_parameter(
    Parameter(
        "Processeds3Bucket",
        Type=STRING,
        Description="Processed bucket which will have the final output",
        Default="processed-hit-level-data",
    )
)

SQSforPublish = t.add_resource(
    Queue("SQSforPublish", VisibilityTimeout =1000
    )
)

ProcessParsedLambdaFunction = t.add_resource(

    Function(
        "ProcessParsedLambdaFunction",
        FunctionName = 'process_parsed_output',
        Code=Code(S3Bucket ='hit-level-data-lambda-codebase', S3Key = 'process_parsed_output.zip'),
        Handler="process_parsed_output.lambda_handler",
        Role=GetAtt("LambdaExecutionRole", "Arn"),
        Runtime="python3.9",
        MemorySize=Ref(MemorySize),
        Timeout=Ref(Timeout),
        Environment = Environment(Variables={'SQSURL': Ref("SQSforPublish"), 'final_bucket' : Ref(Processeds3Bucket),
        'final_output_file_name':'_SearchKeywordPerformance.tsv'}),
        Layers = ['arn:aws:lambda:us-west-2:336392948345:layer:AWSDataWrangler-Python39:8', 'arn:aws:lambda:us-west-2:506446423536:layer:pandas:1']
    )
)

EventSourceMapping = t.add_resource(

    EventSourceMapping("EventSourceMapping",
                        EventSourceArn = GetAtt("SQSforPublish", "Arn"),
                        FunctionName = GetAtt("ProcessParsedLambdaFunction", "Arn"),
                        BatchSize = 1
                        )

    )

DQLambdaFunction = t.add_resource(

    Function(
        "DQLandingHitLevelData",
        FunctionName = 'dq_check_split_file',
        Code=Code(S3Bucket ='hit-level-data-lambda-codebase', S3Key = 'dq_check_split_file.zip'),
        Handler="dq_check_split_file.lambda_handler",
        Role=GetAtt("LambdaExecutionRole", "Arn"),
        Runtime="python3.9",
        MemorySize=Ref(MemorySize),
        Timeout=Ref(Timeout),
        Environment = Environment(Variables={'SNSTopicArn': Ref("DQSnstopic"), 'target_bucket' : Ref(Intermediates3Bucket), 'file_type' : 'text/tab-separated-values',
        'cols_for_analysis' : '["date_time", "ip", "event_list", "product_list", "referrer"]',
        'expected_columns': '["hit_time_gmt", "date_time", "user_agent", "ip", "event_list", "geo_city", "geo_region", "geo_country" , "pagename", "page_url", "product_list", "referrer"]',
        'product_list_split_cols' : '["category", "product_name", "number_of_items", "total_revenue", "custom_event"]'}),
        Layers = ['arn:aws:lambda:us-west-2:336392948345:layer:AWSDataWrangler-Python39:8']
    )
)

s3InvokePermission = t.add_resource(

    Permission(
    "s3InvokePermission",
        Action = 'lambda:InvokeFunction',
        FunctionName = GetAtt("DQLandingHitLevelData", "Arn"),
        Principal = 's3.amazonaws.com',
        SourceArn = 'arn:aws:s3:::landing-hit-level-data'
        )
)

s3InvokePermissionSQS = t.add_resource(

    Permission(
    "s3InvokePermissionSQS",
        Action = 'lambda:InvokeFunction',
        FunctionName = GetAtt("SQSPublishLambdaFunction", "Arn"),
        Principal = 's3.amazonaws.com',
        SourceArn = 'arn:aws:s3:::intermediate-hit-level-data'
        )
)


LambdaExecutionRole = t.add_resource(
    Role(
        "LambdaExecutionRole",
        Path="/",
        Policies=[
            Policy(
                PolicyName="CloudwatchAccess",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["logs:*"],
                            "Resource": "arn:aws:logs:*:*:*",
                            "Effect": "Allow",
                        }
                    ],
                },
            ),
            Policy(
                PolicyName="s3AccessLanding",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["s3:*", "s3-object-lambda:*"],
                            "Resource": [
                                        {"Fn::Join": ["", ["arn:aws:s3:::", {"Ref":"Landings3Bucket"}, "/*" ]]}
                                        ],
                            "Effect": "Allow",
                        }
                    ],
                },
            ),
            Policy(
                PolicyName="s3AccessIntermediate",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["s3:*", "s3-object-lambda:*", "s3:ListBucket"],
                            "Resource": [
                                        {"Fn::Join": ["", ["arn:aws:s3:::", {"Ref":"Intermediates3Bucket"}, "/*" ]]}
                                        ],
                            "Effect": "Allow",
                        }
                    ],
                },
            ),
            Policy(
                PolicyName="s3ListAccessIntermediate",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "s3:ListBucket",
                            "Resource": [
                                        {"Fn::Join": ["", ["arn:aws:s3:::", {"Ref":"Intermediates3Bucket"} ]]}
                                        ],
                            "Effect": "Allow",
                        }
                    ],
                },
            ),
            Policy(
                PolicyName="s3AccessProcessed",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["s3:*", "s3-object-lambda:*"],
                            "Resource": [
                                        {"Fn::Join": ["", ["arn:aws:s3:::", {"Ref":"Processeds3Bucket"}, "/*" ]]}
                                        ],
                            "Effect": "Allow",
                        }
                    ],
                },
            ),
            Policy(
                PolicyName="snsAccess",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "sns:Publish",
                            "Resource": Ref("DQSnstopic"),
                            "Effect": "Allow",
                        }
                    ],
                },
            ),
            Policy(
                PolicyName="sqsAccess",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "sqs:SendMessage",
                            "Resource": GetAtt("SQSforPublish", "Arn"),
                            "Effect": "Allow",
                        }
                    ],
                },
            ),
            Policy(
                PolicyName="sqsWriteDeleteAccess",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action":  [
                                        "sqs:ReceiveMessage",
                                        "sqs:DeleteMessage",
                                        "sqs:GetQueueAttributes",
                                        "logs:CreateLogGroup",
                                        "logs:CreateLogStream",
                                        "logs:PutLogEvents"
                                            ],
                            "Resource": GetAtt("SQSforPublish", "Arn"),
                            "Effect": "Allow",
                        }
                    ],
                },
            ),
            Policy(
                PolicyName="lambdalayerAccess",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["lambda:GetLayerVersion",
                                          "lambda:DeleteLayerVersion",
                                          "lambda:ListLayerVersions",
                                          "lambda:ListLayers",
                                          "lambda:AddLayerVersionPermission",
                                        "lambda:RemoveLayerVersionPermission"
                                                ],
                            "Resource": "*",
                            "Effect": "Allow",
                        }
                    ],
                },
            )
        ],
        AssumeRolePolicyDocument={
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["sts:AssumeRole"],
                    "Effect": "Allow",
                    "Principal": {"Service": ["lambda.amazonaws.com"]},
                }
            ],
        },
    )
)


LambdaConfig= LambdaConfigurations(Event ='s3:ObjectCreated:Put', Function = GetAtt("DQLandingHitLevelData", "Arn"))

S3BucketLanding = t.add_resource(
    Bucket(
        "S3BucketLanding",
        BucketName = Ref(Landings3Bucket),
        AccessControl = Private,
        DependsOn = DQLambdaFunction,
        NotificationConfiguration =  NotificationConfiguration(LambdaConfigurations = [LambdaConfig])
    ))


SQSPublishLambdaFunction = t.add_resource(

    Function(
        "SQSPublishLambdaFunction",
        FunctionName = 'publish_sqs',
        Code=Code(S3Bucket ='hit-level-data-lambda-codebase', S3Key = 'publish_sqs.zip'),
        Handler="publish_sqs.lambda_handler",
        Role=GetAtt("LambdaExecutionRole", "Arn"),
        Runtime="python3.9",
        MemorySize=Ref(MemorySize),
        Timeout=Ref(Timeout),
        Environment = Environment(Variables={'SNSTopicArn': Ref("DQSnstopic"), 'SQSURL': Ref(SQSforPublish) }),
        Layers = ['arn:aws:lambda:us-west-2:336392948345:layer:AWSDataWrangler-Python39:8']
    )
)

FilterRule = Rules(Name = "suffix", Value = ".json")
S3KeyFilter = S3Key(Rules = [FilterRule])
NotificationFilterforIntermediates3 = Filter(S3Key = S3KeyFilter)
LambdaConfigforIntermediates3 = LambdaConfigurations(Event ='s3:ObjectCreated:Put', Filter = NotificationFilterforIntermediates3,
                                                    Function = GetAtt("SQSPublishLambdaFunction", "Arn"))

S3Bucketintermediate = t.add_resource(
    Bucket(
        "S3Bucketintermediate",
        BucketName = Ref(Intermediates3Bucket),
        AccessControl = Private,
        DependsOn = SQSPublishLambdaFunction,
        NotificationConfiguration =  NotificationConfiguration(LambdaConfigurations = [LambdaConfigforIntermediates3])
    )
)

S3Bucketprocessed = t.add_resource(
    Bucket(
        "S3Bucketprocessed",
        BucketName = Ref(Processeds3Bucket),
        AccessControl = Private
    )
)

sns_topic = t.add_resource(
    Topic(
        "DQSnstopic",
        TopicName = "Success_topic",
        Subscription = [Subscription(
                "snssubscription",
                Protocol  = 'email',
                Endpoint = 'vwalvekar90@gmail.com'
            )
        ]
    )
)

with open("cft_template.yaml", 'w') as f:
    f.write(t.to_yaml())
