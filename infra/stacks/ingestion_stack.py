from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
    aws_s3 as s3,
    CfnOutput
)
from constructs import Construct
from apify_client import ApifyClient
from dotenv import load_dotenv

import os

load_dotenv()


class IngestionStack(Stack):
    """
    Creates the complete data ingestion pipeline:
    - 6 Lambda functions for data processing
    - Step Function to orchestrate the pipeline
    
    Uses Qdrant Cloud for vector storage.
    """
    
    def __init__(
        self,
        scope: Construct,
        id: str,
        data_bucket: s3.IBucket,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)
        
        # -------------------------
        # Configuration Variables
        # -------------------------
        APIFY_TOKEN = os.getenv("APIFY_TOKEN")
        QDRANT_URL = os.getenv("QDRANT_URL")
        QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
        
        # -------------------------
        # Lambda Functions
        # -------------------------
        
        # 1. Scrape LinkedIn
        scrape_linkedin = _lambda.Function(
            self, "ScrapeLinkedIn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler" ,
            code=_lambda.Code.from_asset("../../lambdas/scrape_linkedin"),
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                "APIFY_TOKEN": APIFY_TOKEN
            }
        )
        data_bucket.grant_write(scrape_linkedin, "data/raw/linkedin/*")
        
        # 2. Scrape YouTube
        scrape_youtube = _lambda.Function(
            self, "ScrapeYouTube",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../../lambdas/scrape_youtube"),
            timeout=Duration.minutes(10),
            memory_size=512
        )
        data_bucket.grant_read_write(scrape_youtube)
        
        # 3. Clean Data
        clean_data = _lambda.Function(
            self, "CleanData",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../../lambdas/clean_data"),
            timeout=Duration.minutes(5),
            memory_size=512
        )
        data_bucket.grant_read_write(clean_data)
        
        # 4. Chunk Data
        chunk_data = _lambda.Function(
            self, "ChunkData",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../../lambdas/chunk_data"),
            timeout=Duration.minutes(3),
            memory_size=1024
        )
        data_bucket.grant_read_write(chunk_data)
        
        # 5. Generate Embeddings (Docker image for large ML model)
        generate_embeddings = _lambda.DockerImageFunction(
            self, "GenerateEmbeddings",
            code=_lambda.DockerImageCode.from_image_asset(
                "../../lambdas/generate_embeddings"
            ),
            timeout=Duration.minutes(15),
            memory_size=3072,  # 3GB for model loading
            environment={
                "MODEL_NAME": "mixedbread-ai/mxbai-embed-large-v1"
            }
        )
        data_bucket.grant_read_write(generate_embeddings)
        
        # 6. Store in Qdrant Cloud
        store_qdrant = _lambda.Function(
            self, "StoreQdrant",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../../lambdas/store_qdrant"),
            timeout=Duration.minutes(10),
            memory_size=1024,
            environment={
                "QDRANT_URL": QDRANT_URL,
                "QDRANT_API_KEY": QDRANT_API_KEY
            }
        )
        data_bucket.grant_read(store_qdrant, "data/embedded/*")
        
        # -------------------------
        # Step Function Tasks
        # -------------------------
        
        # Task 1: Scrape LinkedIn
        scrape_linkedin_task = tasks.LambdaInvoke(
            self, "ScrapeLinkedInTask",
            lambda_function=scrape_linkedin,
            payload=sfn.TaskInput.from_object({
                "profile_url": "https://www.linkedin.com/in/lennyrachitsky/",
                "count": 100,
                "output_bucket": data_bucket.bucket_name,
                "output_prefix": "data/raw/linkedin/"
            }),
            result_path="$.linkedin_result",
            retry_on_service_exceptions=True
        )
        
        # Task 2: Scrape YouTube
        scrape_youtube_task = tasks.LambdaInvoke(
            self, "ScrapeYouTubeTask",
            lambda_function=scrape_youtube,
            payload=sfn.TaskInput.from_object({
                "input_bucket": data_bucket.bucket_name,
                "video_ids_key": "data/raw/youtube/video_ids.txt",
                "output_bucket": data_bucket.bucket_name,
                "output_prefix": "data/raw/youtube/transcripts/"
            }),
            result_path="$.youtube_result",
            retry_on_service_exceptions=True
        )
        
        # Task 3: Clean Data
        clean_data_task = tasks.LambdaInvoke(
            self, "CleanDataTask",
            lambda_function=clean_data,
            payload=sfn.TaskInput.from_object({
                "input_bucket": data_bucket.bucket_name,
                "input_prefixes": [
                    "data/raw/linkedin/",
                    "data/raw/youtube/transcripts/"
                ],
                "output_bucket": data_bucket.bucket_name,
                "output_prefixes": [
                    "data/processed/linkedin/",
                    "data/processed/youtube/"
                ]
            }),
            result_path="$.clean_result",
            retry_on_service_exceptions=True
        )
        
        # Task 4: Chunk Data
        chunk_data_task = tasks.LambdaInvoke(
            self, "ChunkDataTask",
            lambda_function=chunk_data,
            payload=sfn.TaskInput.from_object({
                "input_bucket": data_bucket.bucket_name,
                "input_prefixes": [
                    "data/processed/linkedin/",
                    "data/processed/youtube/"
                ],
                "output_bucket": data_bucket.bucket_name,
                "output_key": "data/chunks/final_chunks.json"
            }),
            result_path="$.chunk_result",
            retry_on_service_exceptions=True
        )
        
        # Task 5: Generate Embeddings
        # generate_embeddings_task = tasks.LambdaInvoke(
        #     self, "GenerateEmbeddingsTask",
        #     lambda_function=generate_embeddings,
        #     payload=sfn.TaskInput.from_object({
        #         "input_bucket": data_bucket.bucket_name,
        #         "chunks_key": "data/chunks/final_chunks.json",
        #         "output_bucket": data_bucket.bucket_name,
        #         "output_key": "data/embedded/mxbai_corpus.pt"
        #     }),
        #     result_path="$.embedding_result",
        #     retry_on_service_exceptions=True
        # )
        
        generate_embeddings_task = tasks.LambdaInvoke(
            self, "GenerateEmbeddingsTask",
            lambda_function=generate_embeddings,
            payload=sfn.TaskInput.from_object({
                "bucket": data_bucket.bucket_name,      
                "input_key": "data/chunks/final_chunks.json", 
                "output_key": "data/embedded/mxbai_corpus.pt"
            }),
            result_path="$.embedding_result",
            retry_on_service_exceptions=True
        )
                
        # Task 6: Store in Qdrant Cloud
        store_qdrant_task = tasks.LambdaInvoke(
            self, "StoreQdrantTask",
            lambda_function=store_qdrant,
            payload=sfn.TaskInput.from_object({
                "input_bucket": data_bucket.bucket_name,
                "embeddings_key": "data/embedded/mxbai_corpus.pt",
                "collection_name": "virtual-lenny",
                "recreate_collection": False  # Set to True to force recreate
            }),
            result_path="$.qdrant_result",
            retry_on_service_exceptions=True
        )
        
        # -------------------------
        # Orchestration with Error Handling
        # -------------------------
        
        # Run scrapers in parallel
        parallel_scraping = sfn.Parallel(
            self, "ParallelScraping",
            result_path="$.scraping_results",
            comment="Scrape LinkedIn and YouTube data in parallel"
        )
        parallel_scraping.branch(scrape_linkedin_task)
        parallel_scraping.branch(scrape_youtube_task)
        
        # Success state
        success_state = sfn.Succeed(
            self, "PipelineSuccess",
            comment="Data ingestion pipeline completed successfully"
        )
        
        # Failure states for each stage
        scraping_failed = sfn.Fail(
            self, "ScrapingFailed",
            cause="Failed to scrape data from LinkedIn or YouTube",
            error="ScrapingError"
        )
        
        cleaning_failed = sfn.Fail(
            self, "CleaningFailed",
            cause="Failed to clean scraped data",
            error="CleaningError"
        )
        
        chunking_failed = sfn.Fail(
            self, "ChunkingFailed",
            cause="Failed to chunk processed data",
            error="ChunkingError"
        )
        
        embedding_failed = sfn.Fail(
            self, "EmbeddingFailed",
            cause="Failed to generate embeddings",
            error="EmbeddingError"
        )
        
        qdrant_failed = sfn.Fail(
            self, "QdrantStorageFailed",
            cause="Failed to store embeddings in Qdrant Cloud",
            error="QdrantStorageError"
        )
        
        # Chain everything together with error handling at each stage
        definition = (
            parallel_scraping
            .add_catch(scraping_failed, errors=["States.ALL"])
            .next(clean_data_task)
            .add_catch(cleaning_failed, errors=["States.ALL"])
            .next(chunk_data_task)
            .add_catch(chunking_failed, errors=["States.ALL"])
            .next(generate_embeddings_task)
            .add_catch(embedding_failed, errors=["States.ALL"])
            .next(store_qdrant_task)
            .add_catch(qdrant_failed, errors=["States.ALL"])
            .next(success_state)
        )
        
        # Create state machine
        self.state_machine = sfn.StateMachine(
            self, "IngestionPipeline",
            definition=definition,
            timeout=Duration.minutes(45),
            comment="Virtual Lenny Data Ingestion Pipeline - Orchestrates scraping, cleaning, chunking, embedding, and Qdrant Cloud storage"
        )
        
        # -------------------------
        # Outputs
        # -------------------------
        
        CfnOutput(
            self, "StateMachineArn",
            value=self.state_machine.state_machine_arn,
            description="ARN of the ingestion pipeline state machine",
            export_name="VirtualLennyStateMachineArn"
        )
        
        CfnOutput(
            self, "StateMachineName",
            value=self.state_machine.state_machine_name,
            description="Name of the ingestion pipeline state machine"
        )
        
        CfnOutput(
            self, "StateMachineConsoleUrl",
            value=f"https://console.aws.amazon.com/states/home?region={self.region}#/statemachines/view/{self.state_machine.state_machine_arn}",
            description="AWS Console URL for the state machine"
        )