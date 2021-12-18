# High level overview
This CDK stack defines Lambda functions to iterate through oceanographic data files in parallel.
The functions compute some aggregate representation for each file, then save the result to a database.
<br><br>
A GitHub Actions workflow to build and deploy any changes made on each push is also included.
<br><br>
![Diagram of CDK stack](diagram.png)
<br>
We can follow this flowchart to better understand the flow of data through the stack. Implementation details are omitted here, and included in sections below. 
<br><br>
1. Our **Orchestrator Function** first iterates through files stored in a **Data Store**.
2. For each file, it identifies the type of file, and hands off the reference to a **Queue** for the appropriate **Handler Function** (Or saves to the **Failure Log** if it cannot identify the file type).
3. The **Handler Functions** process through the file references in the **Queue**, and attempt to compute some kind of aggregate. If successful, they save the result to an **Aggregation Stats DB**. Otherwise, they log to the **Failure Log**.

# Stack Specification
Most of the infrastructure is specified in this Python file: [`data_review_stack.py`](data_review/data_review_stack.py). This is the file that you should change if you want to hook up the stack to an external S3 bucket, use a different DBMS, etc. 

# Data Store
In this stack, the Data Store is implemented as an S3 bucket. It uses [s3deploy](https://docs.aws.amazon.com/cdk/api/latest/docs/aws-s3-deployment-readme.html) to load any data in the `test_data/` directory into the bucket (under the hood, this creates another lambda function that is only called when the stack is created or updated).
<br><br>
Apart from the deployment lambda function, all lambda functions have **read-only** access to the bucket.
### TODO:

# Lambda Functions
Lambda functions are specified in [`data_review_stack.py`](data_review/data_review_stack.py) - here you can change the memory allocation, max runtime, execution environment, etc. The actual function logic can be found in the `lambda/` directory.

# Queue
Currently, there is no queue implemented - the Orchestrator Function directly calls the Handler Functions. Using a queue has the benefit of being able to limit the concurrency of the Handler Functions (you could just change the `reserved_concurrent_executions` attribute in the specification for the Lambda Functions, but this would mean any calls that would go over the concurrency limit will fail, instead of waiting to be called later).

A queue is not necessary for the basic functionallity described. However, if one wanted to add a queue to the implementation, they could use [SQS](https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_sqs/README.html).

# Welcome to your CDK Python project!

This is a blank project for Python development with CDK.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
