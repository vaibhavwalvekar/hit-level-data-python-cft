<h3>Readme</h3>
This is an application which deploys AWS resources to build out a data pipeline to process hit level data (visitors visiting client website), to provide analytical answers to the business. The analytical question answered is :<br/>
<br/>
How much revenue is the client getting from external Search Engines, such as Google, Yahoo and MSN, and which keywords are performing the best based on revenue?<br/>
<br/>
To answer the above question, the design is put in place to build a robust, scalable, decoupled and governed data pipeline with proper systems to notify/log success/ failure/ retires, etc. The design is also simplified keeping in mind the project timelines and resources.<br/>
The design workflow doc can be found at https://github.com/vaibhavwalvekar/hit-level-data-python-cft/blob/main/application_workflow_diagram.jpeg<br/>
<br/>
The workflow diagram explains at a high level the steps involved in this pipeline. The description about each of the .py file and their functions is described respectively in those files. At a high level, the three .py files correspond to 3 AWS lambda functions, below are their names and descriptions:<br/>
1. dq_check_split_file.py - Does DQ checks, unpacking of columns and splitting of input file into smaller files.<br/>
2. publish_sqs.py - Publishes message to SQS to act as a decoupled input to third lambda function.<br/>
3. process_parsed_output.py - Processes the file as a dataframe to unpack/ calculate other columns which help in answering the analytical question on hand.<br/>

<h4>Deployment requirements:</h4>
1. Require aws programmatic access, with sufficient privileges to create resource using cloudformation templates via amazon cli OR use the cft_template.yaml to create cloudformation templates using AWS console.

<h4>Deployment Steps:</h4>
1. Run deploy_stack.sh -- Creates all the required resources with appropriate permission, takes about 3 mins to create the infrastructure.

<h4>Execution Steps:</h4>
1. Upload a file in landing bucket (data.tsv) -- This will trigger the process of doing DQ, transforming and splitting files and eventually running logic to answer the analytical question. The output will be stored in the Processed s3 bucket. <br/>For processing of sample data, end to end is less than a min.<br/>
    i. Sample input file provided is found at - https://github.com/vaibhavwalvekar/hit-level-data-python-cft/blob/main/data.tsv<br/>
    ii. Sample output file to answer the above analytical question can be found at - https://github.com/vaibhavwalvekar/hit-level-data-python-cft/blob/main/2022-07-08_SearchKeywordPerformance.tsv<br/>

<h4>Business Case Analysis:</h4>
https://github.com/vaibhavwalvekar/hit-level-data-python-cft/blob/main/business_case_analysis.md
