import boto3
import argparse
import os
from botocore.exceptions import ProfileNotFound, ClientError

def s3_manager():
    parser = argparse.ArgumentParser(description="S3 File Manager")
    parser.add_argument("bucket", help="Name of the S3 bucket")
    parser.add_argument("-p", "--profile", help="AWS profile name", default="default")
    parser.add_argument("-d", "--download", help="File key to download from S3")
    parser.add_argument("-u", "--upload", help="Local file path to upload to S3")
    args = parser.parse_args()

    try:
        session = boto3.Session(profile_name=args.profile)
        s3 = session.client('s3')
        
        # --- UPLOAD ---
        if args.upload:
            if not os.path.isfile(args.upload):
                print(f"Error: Local file '{args.upload}' does not exist.")
                return
            
            file_name = os.path.basename(args.upload)
            print(f"Uploading {args.upload} to {args.bucket}...")
            s3.upload_file(args.upload, args.bucket, file_name)
            print(f"Successfully uploaded {file_name}!")
            return 

        # --- LIST ---
        print(f"--- Bucket: {args.bucket} | Profile: {args.profile} ---")
        response = s3.list_objects_v2(Bucket=args.bucket)
        
        if 'Contents' in response:
            for obj in response['Contents']:
                print(f"-> {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("Bucket is empty or access denied.")

        # --- DOWNLOAD ---
        file_to_get = args.download
        if not file_to_get:
            file_to_get = input("\nEnter a filename to download (or press Enter to exit): ").strip()

        if file_to_get:
            local_dir = os.path.dirname(file_to_get)
            if local_dir and not os.path.exists(local_dir):
                print(f"Creating local directory: {local_dir}")
                os.makedirs(local_dir)

            print(f"Downloading {file_to_get}...")
            s3.download_file(args.bucket, file_to_get, file_to_get)
            print(f"Success! Saved to {os.getcwd()}/{file_to_get}")

    except ProfileNotFound:
        print(f"Error: Profile '{args.profile}' not found.")
    except ClientError as e:
        print(f"AWS Error: {e.response['Error']['Message']}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    s3_manager()
