import json
import boto3
import botocore
import datetime
import time


def describeami(client,inputDate):
    amidescribe = client.describe_images(
    Owners=[
        '811038047831',
    ]
    )
    
    check  = amidescribe['Images']
    
    for i in check:
        aId = i['ImageId']
        block = i["BlockDeviceMappings"]
        '''print("Image Id is :",aId)'''
        
        inputdate = str(inputDate)
        creation = i['CreationDate']
        
        if inputdate in creation:
            try:
                response = client.deregister_image(
                        ImageId=aId,
                )
                print(response)
            except botocore.exceptions.ClientError as e:
                print(e)
        else:
            print("Ami not present in year :",inputDate)
        
def describesnapshot(client,inputDate):
    snapshotdescribe = client.describe_snapshots(
        
        OwnerIds=[
        '811038047831',
        ]
        )
    data  = snapshotdescribe["Snapshots"]
    '''print(data)'''
    
    inputdate = int(inputDate)
    for i in data:
        sId = i['SnapshotId']
        time = i["StartTime"]
        
        date  = int(time.year)
        
        
        if inputdate == date :
            try:
                '''response = client.deregister_image(
                    ImageId='',
                )'''
                response = client.delete_snapshot(
                    SnapshotId=sId,
                )
                print(response)
            except botocore.exceptions.ClientError as e:
                print(e)
                
        else:
            print("Snapshots not present in year :", inputdate) 

        
        
    

def lambda_handler(event, context):
    
    inputDate = '2019'
    
    client = boto3.client('ec2')
    
    describeami(client,inputDate)
    
    describesnapshot(client,inputDate)
    
    
    
    

    
            

    

        
        
