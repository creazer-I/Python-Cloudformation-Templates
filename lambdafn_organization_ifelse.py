import json
import boto3
import botocore


def lambda_handler(event, context):
    
    email = 'remem58694@upshopt.comm'
    
    client = boto3.client('organizations')
    s3 = boto3.client('s3')
    
    list = client.list_accounts(
    MaxResults=20
    )
    
    
    check = json.dumps(list["Accounts"],sort_keys=True, default=str)
    
    response = list["Accounts"]
        
        
    if email in check:
        for i in response:
            id = i["Id"]
            mail = i["Email"]
            if email == mail:
                print(mail,id)
            else:
                pass
        
            
    else:
        try:
            print(email,"is not there")
            bucket = s3.create_bucket(
            ACL='private',
            Bucket="emailidnjhb11cc3djfwnfw",
            CreateBucketConfiguration={
                'LocationConstraint': 'ap-southeast-2' }
            )
            print(bucket)
            
            return {
            'statusCode': 200,
            'body': json.dumps(bucket)
            }
            
        except botocore.exceptions.ClientError as e:
            print(e)
                    
        
        
    
