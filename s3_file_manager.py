import boto3
import argparse
import os
from botocore.exceptions import ProfileNotFound, ClientError

def s3_manager():
    parser = argparse.ArgumentParser(description="S3 File Manager")
    parser.add_argument("bucket", help="Name of the S3 bucket")
    parser.add_argument("-p", "--profile", help="AWS profile name", default="default")
    parser.add_argument("-d", "--download", help="File name to download (relative to prefix)")
    parser.add_argument("-u", "--upload", help="Local file path to upload")
    parser.add_argument("--prefix", help="S3 folder/prefix for all operations", default="")
    args = parser.parse_args()

    try:
        session = boto3.Session(profile_name=args.profile)
        s3 = session.client('s3')
        
        prefix = args.prefix.strip('/')
        if prefix:
            prefix += '/'

        # --- UPLOAD ---
        if args.upload:
            if not os.path.isfile(args.upload):
                print(f"Error: Local file '{args.upload}' not found.")
                return
            
            s3_key = f"{prefix}{os.path.basename(args.upload)}"
            print(f"Uploading {args.upload} to s3://{args.bucket}/{s3_key}...")
            s3.upload_file(args.upload, args.bucket, s3_key)
            print("Upload Successful!")
            return

        # --- LIST ---
        print(f"--- Bucket: {args.bucket} | Profile: {args.profile} | Prefix: '{prefix}' ---")
        response = s3.list_objects_v2(Bucket=args.bucket, Prefix=prefix)
        
        if 'Contents' in response:
            for obj in response['Contents']:
                print(f"-> {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("No objects found matching that prefix.")

        # --- DOWNLOAD ---
        file_to_get = args.download
        if not file_to_get:
            file_to_get = input("\nEnter file name/key to download (or Enter to exit): ").strip()

        if file_to_get:
            if prefix and not file_to_get.startswith(prefix):
                s3_key = f"{prefix}{file_to_get}"
            else:
                s3_key = file_to_get

            local_filename = os.path.basename(s3_key)
            
            print(f"Downloading {s3_key} as {local_filename}...")
            s3.download_file(args.bucket, s3_key, local_filename)
            print(f"Success! Saved to {os.getcwd()}/{local_filename}")

    except ProfileNotFound:
        print(f"Error: Profile '{args.profile}' not found in ~/.aws/credentials")
    except ClientError as e:
        print(f"AWS Error: {e.response['Error']['Message']}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    s3_manager()
