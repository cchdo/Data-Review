from aws_cdk import (
    core as cdk,
    aws_sqs as sqs,
    aws_lambda as _lambda,
    aws_dynamodb as ddb,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core


class DataReviewStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        data_bucket = s3.Bucket(
            self, "DataBucket",
            removal_policy = core.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        s3deploy.BucketDeployment(self, "DeployTestData",
            sources=[s3deploy.Source.asset("./test_data")],
            destination_bucket=data_bucket,
        )
        
        #Helper data structures
        file_process_queue = sqs.Queue(self, "FileProcessQueue")
        aggregate_results_db = ddb.Table(
            self, "AggregateResultsDB",
            partition_key=ddb.Attribute(name="filename", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST
        )

        #What should we log here? Can a file only fail once - making file key primary key?
        #Or log every failure and make timestamp + entropy the primary key?
        failure_log_db = ddb.Table(
            self, "FailureLogDB",
            partition_key=ddb.Attribute(name="filename", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST
        )

        LAMBDA_ENVS = {
            "S3_BUCKET_NAME": data_bucket.bucket_name,
            "FILE_PROCESS_QUEUE": file_process_queue.queue_name,
            "RESULTS_TABLE": aggregate_results_db.table_name,
            "FAILURE_TABLE": failure_log_db.table_name,
        }
        #Lambda functions
        bottle_handler_lambda = _lambda.Function(
            self, "BottleHandlerLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='index.handler',
            code=_lambda.Code.from_asset(
                "lambda/orchestrator",
                bundling=core.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_8.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install --no-cache -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                ),
            ),
            environment=LAMBDA_ENVS,
            timeout=core.Duration.minutes(10),
            profiling=True,
        )

        ctd_handler_lambda = _lambda.Function(
            self, "ctdHandlerLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='index.handler',
            code=_lambda.Code.from_asset(
                "lambda/ctd_handler",
                bundling=core.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_8.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install --no-cache -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                ),
            ),
            environment=LAMBDA_ENVS,
            timeout=core.Duration.minutes(10),
            profiling=True,
        )
        LAMBDA_FUNC_NAMES = {
            "BOTTLE_HANDLER_FUNC_NAME": bottle_handler_lambda.function_name,
            "CTD_HANDLER_FUNC_NAME": ctd_handler_lambda.function_name,
        }
        orchestrator_lambda = _lambda.Function(
            self, "OrchestratorLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='index.handler',
            code=_lambda.Code.from_asset(
                "lambda/orchestrator",
                bundling=core.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_8.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install --no-cache -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                ),
            ),
            environment={**LAMBDA_ENVS, **LAMBDA_FUNC_NAMES},
            timeout=core.Duration.minutes(10),
            profiling=True,
        )

        #Grant lambdas bucket access
        data_bucket.grant_read(orchestrator_lambda)
        data_bucket.grant_read(bottle_handler_lambda)
        data_bucket.grant_read(ctd_handler_lambda)

        #Allow the orchestrator lambda to invoke the other lambdas
        bottle_handler_lambda.grant_invoke(orchestrator_lambda)
        ctd_handler_lambda.grant_invoke(orchestrator_lambda)
        
        #Database write permissions
        aggregate_results_db.grant_write_data(bottle_handler_lambda)
        aggregate_results_db.grant_write_data(ctd_handler_lambda)
        failure_log_db.grant_write_data(bottle_handler_lambda)
        failure_log_db.grant_write_data(ctd_handler_lambda)