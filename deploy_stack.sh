aws s3 mb s3://hit-level-data-lambda-codebase

aws s3 cp dq_check_split_file.zip s3://hit-level-data-lambda-codebase
aws s3 cp publish_sqs.zip s3://hit-level-data-lambda-codebase
aws s3 cp process_parsed_output.zip s3://hit-level-data-lambda-codebase

aws cloudformation deploy \
    --template-file cft_template.yaml \
    --stack-name ProcessHitLevelData \
    --region "us-west-2" \
    --capabilities CAPABILITY_NAMED_IAM


#aws cloudformation delete-stack --stack-name ProcessHitLevelData
