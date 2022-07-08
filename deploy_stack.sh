rm -f dq_check_split_file.zip publish_sqs.zip process_parsed_output.zip

zip -r dq_check_split_file.zip numpy numpy-1.23.0.dist-info numpy.libs dq_check_split_file.py
zip -r publish_sqs.zip publish_sqs.py
zip -r process_parsed_output.zip process_parsed_output.py

aws s3 mb s3://hit-level-data-lambda-codebase

aws s3 cp dq_check_split_file.zip s3://hit-level-data-lambda-codebase
aws s3 cp publish_sqs.zip s3://hit-level-data-lambda-codebase
aws s3 cp process_parsed_output.zip s3://hit-level-data-lambda-codebase

python3 create_cft_yaml.py

aws cloudformation deploy \
    --template-file cft_template.yaml \
    --stack-name ProcessHitLevelData \
    --region "us-west-2" \
    --capabilities CAPABILITY_NAMED_IAM


#aws cloudformation delete-stack --stack-name ProcessHitLevelData
