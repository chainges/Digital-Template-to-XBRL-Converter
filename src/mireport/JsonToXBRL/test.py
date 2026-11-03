from google.cloud import storage

BUCKET_NAME = "vsme-generated-reports"

client = storage.Client()

bucket = client.bucket(BUCKET_NAME)

print("Connected to Google Cloud!")
print("Bucket:", bucket.name)