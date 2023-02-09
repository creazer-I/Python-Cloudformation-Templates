# These are the libraries that are being imported.
import json
import boto3
import botocore
import datetime
import time


def describeami(client,inputDate):
    """
    It takes the client and the input date as parameters and then it checks if the input date is present
    in the creation date of the AMI. If it is present, it deregisters the AMI
    
    :param client: The boto3 client object
    :param inputDate: The date you want to delete AMIs from
    """
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
    """
    It takes a client object and a date as input and deletes all snapshots created in that year
    
    :param client: The boto3 client object
    :param inputDate: The year for which you want to delete the snapshots
    """
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
    """
    It takes the input date, and then calls the describeami and describesnapshot functions, passing the
    input date as a parameter.
    
    :param event: This is the event that triggered the lambda function
    :param context: It's a Lambda-specific object that contains information about the invocation,
    function, and execution environment
    """
    
    inputDate = '2019'
    
    client = boto3.client('ec2')
    
    describeami(client,inputDate)
    
    describesnapshot(client,inputDate)
