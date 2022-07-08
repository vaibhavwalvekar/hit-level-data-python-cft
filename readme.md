This is a application which deploys AWS resources to build out a pipeline to process hit level data, which is a tab separated file to provide analytical answers to the business. The analytical question answered is :

How much revenue is the client getting from external Search Engines, such as Google, Yahoo and MSN, and which keywords are performing the best based on revenue?

To answer the above question, the design is put in place to build a robust, scalable, decoupled and governed data pipeline with proper systems to notify/log success/ failure/ retires, etc. The design is also simplified keeping in mind the project timelines and resources. The design workflow doc can be found at -

The workflow diagram explains at a high level the steps involved in this pipeline. The description about each of the .py file and their functions is described respectively in those files. At a high level, the three .py files correspond to AWS lambda functions, below are their names and descriptions:
1.
2.
3.


Deployment requirements:
1. Require aws programmatic access, with sufficient privileges to create resource using cloudformation templates via amazon cli OR use the cft_template.yaml to create cloudformation templates using AWS console.

Deployment Steps:
1. Run deploy_stack.sh -- Creates all the required resources with appropriate permission, take about 5 mins to create the infrastructure.

Execution Steps:
1. Upload a file in landing bucket (data.tsv) -- This will trigger the process of doing DQ, transforming and splitting files and eventually running logic to answer the analytical question. The output will be stored in the Processed s3 bucket.
    i. Sample input file provided is found at -
    ii. Sample output file to answer the above analytical question can be found at -

Business Case Analyzed:

Problem Statement:
How much revenue is the client getting from external Search Engines, such as Google, Yahoo and MSN, and which keywords are performing the best based on revenue?

Exploration of Sample Dataset:
  1. It is data about visitors journey on the client's website.
  2. The grain can be identified as the event actions taken by the visitor on the website.
  3. Many different actions of the user are captured in the dataset with a timeline.
  4. Product level details are captured for the visitor only when the action type is Purchase.

The main challenge with respect to the problem statement and understanding the dataset seems to be that of matching the start of a journey to the end of a journey for each visitor, mostly we are interested in the visitor who provided our client some revenue. For that purpose, the columns of interest can be narrowed down to as below:
    date_time	- Needed for defining the timeline, partitioning the data
    ip	- Needed for partitioning the data
    event_list	- Identifying which user are purchasing, hence generating revenue.
    product_list	- It provides the attributes of the product, mainly total_revenue
    referrer - It is a URL, which has important information like search keyword and search engine domain.

Assumption/ Call outs:
  1. Ip identifies a single user
  2. If the same user buys multiple products, even though different category, initial search keyword and search engine domain will be allocated that revenue, as there was no new search.
  3. It there is a new search keyword or use of different search engine domain before end of purchase of the first item, then latest search keyword and search engine will be allocated that revenue, as there is no way to tell if the first search or second search resulted in buy of the first item.
  4. 'p=search' or 'q=search' are the only ways Google, MSN and Bing add search query to their URL, if there are other ways we might have to include that and also we will have to include other patterns for other search engines.

We can answer the clients question with above assumptions in mind by
  1. Firstly unpacking the unstructured columns like the product and referrer to relevant columns, like total_revenue, search_keyword and search engine domain.
  2. Sorting data based on ip and date_time
  3. Only the rows which have external search engines, will have search word, rest rows will have null.
  4. Iterating over the sorted dataset, hold the search keyword and search engine domain name in a variable.
  5. Do the above till we find a total_revenue thats not null and the event_type = 1, if we don't find a total_revenue thats not null before the a new set of search keyword and search key engine, discard the old values and look for revenue with new set of search keywords and search engine domain.

Recommendations:
  1. Above solution represents the python functional programming way of solving the solution, the solution will be simpler in a database. Also, with MPP systems, it should be way quicker than in-memory calculations if we are thinking about scale. AWS EMR, Redshift are better products to implement this use case.
  2. If this processing has to be non-database solution, AWS EC2 will work better with scalability, Lambda with its 15 mins max timeout and restricted memory can be a bottleneck.  
  3. With respect to business case, one recommendation that can be provided is to look for other metrics like count from search engine domains, percentage of drop outs on internal pages, etc which can further help drive discussions
