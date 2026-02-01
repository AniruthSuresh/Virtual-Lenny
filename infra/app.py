import aws_cdk as cdk
from stacks.storage_stack import StorageStack
from stacks.ingestion_stack import IngestionStack

app = cdk.App()

# This "captures" your existing virtual-lenny-bucket
storage = StorageStack(app, "VirtualLennyStorageStack")

# # 2. Initialize the Ingestion Stack
# We pass the bucket object (storage.bucket) to the ingestion pipeline
IngestionStack(
    app, 
    "VirtualLennyIngestionStack",
    data_bucket=storage.bucket
)

app.synth()

