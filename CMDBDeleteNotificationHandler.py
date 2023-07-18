import json
import boto3
import botocore
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

def sendDeleteDBSNSNotification(targetRoleArn,dbArn, snsTopic,function_name, *configurationValues):
    sns_topic = snsTopic
    message = []
    message.append("The following Database has just been deleted")
    message.append("\n")
    message.append("\n")
    message.append("ARN: " + dbArn)
    message.append("\n")
    message.append("\r\n")
    message.append("\r\n")
    message.append("This message is being sent from the function: " + function_name + " to the topic: " + snsTopic +  "\n")
		    
    message = ''.join(message)
    sts_client = boto3.client('sts')
    assumed_role = sts_client.assume_role(RoleArn=targetRoleArn, RoleSessionName='AssumedRoleSession')
    credentials = assumed_role['Credentials']
    
    sns_client = boto3.client(
        'sns',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
    
    configValuesPresent = False
    
    if configurationValues:
        configValuesPresent = True
        value1 = configurationValues[0]
        value2 = configurationValues[1]
        value3 = configurationValues[2]
    
    if configValuesPresent:
        
        snsPublishResult = sns_client.publish(
            TopicArn= sns_topic,
            Message = message,
            
            Subject = ("EH Cloud Database Services Delete Notification for "+ value1 +':' + value2  +':' + value3)
            )
    else:
        snsPublishResult = sns_client.publish(
            TopicArn = sns_topic, 
            Message = message,
            Subject =  "EH Cloud Database Services Delete Notification") 
    
def pushToHubS3Bucket(targetRoleArn, inventoryFile, keyName, bucketName):
    logging.info("^^^^^^^^^^^^^^^^^^^^Inside pushToHubS3Bucket ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    logging.info("Keyname: " + keyName)
	
    
    sts_client = boto3.client('sts')
    assumed_role = sts_client.assume_role(RoleArn=targetRoleArn, RoleSessionName='AssumedRoleSession')
    
    credentials = assumed_role['Credentials']
    
    s3client = boto3.client(
        's3',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
    
    with open(inventoryFile, 'rb') as file:
        file_data = file.read()
        
    putobject  = s3client.put_object(
        Body=file_data,
        Bucket=bucketName,
        Key=keyName
    )
        
    return True

def CMDBDeleteNotificationHandler(event, context):
    
    targetRoleArn =os.environ['targetRoleArn']     
    bucketName =os.environ['targetBucket']
    snsTopic =os.environ['dam_db_status_topic']
    #vpcEndpoint = os.environ['vpc_endpoint']
    regions = os.environ['region']
    function_name = context.function_name

    events = event['detail']

    logging.info("============================Delete DB Notification Handler Begin processing:=================================== ")
    
    logging.info('Event for delete :', events)
    eventName = events['eventName']

    if eventName != 'DeleteTable' and eventName != 'DeleteDBInstance' and eventName != 'DeleteCluster':
        logging.info("Not a DeleteDBInstance or DeleteTable or DeleteCluster Event")
        return "Not a DeleteTable/Instance/Cluster Event"
    
    dateString = datetime.now().strftime('%d%m%Y')

    source = events['eventSource']
    accountId = events['userIdentity']['accountId']

    if source == 'dynamodb.amazonaws.com':
        logging.info('DynamoDB: DeleteTable event')

        tableName = events['requestParameters']['tableName']

        tableArn = events['responseElements']['tableDescription']['tableArn']

        tableIdentityElement = events['responseElements']['tableDescription']['tableId']

        logging.info("DynamoDB: TableArn: " + tableArn)

        logging.info("DynamoDB: Sending notification... ")

        isNotificationSent =  sendDeleteDBSNSNotification(targetRoleArn,tableArn, snsTopic, function_name, regions,accountId, tableName )
        if (isNotificationSent == True):
            logging.info("DynamoDB: Success! Sent message to SNS Topic: " + snsTopic)
        else:
            logging.warning("DynamoDB: Fail! Failed to send message to SNS Topic: " + snsTopic)


        deleteStatusFile = Path('/tmp/wdb-inventory_' + tableName + '.properties')
        isFileCreated = False
        try:
            open(deleteStatusFile, 'a').close()
            isFileCreated = True
        except IOError as ioe:
            logging.error("DynamoDB: Exception when creating a file: " + str(ioe))
            return "DynamoDB: Unable to create a file"
        
        if isFileCreated:
            logging.info('DynamoDB: deleteStatusFile created successfully')
        else:
            logging.warning('DynamoDB: Failed to create deleteStatusFile')
            return "DynamoDB: Failed to create a file"
        
        keyName = "Anthem-Cloud-Databases/" + dateString + "/" +  accountId + "_" + regions + "_" + "dynamodb" + "_" + tableIdentityElement + "_" + tableName + "_deleted.properties"

        logging.info('DynamoDB: Sending file to S3 : ' + bucketName + ", Key: " + keyName)

        isS3WriteSuccessfull = pushToHubS3Bucket(targetRoleArn, deleteStatusFile, keyName, bucketName)
        if isS3WriteSuccessfull != True:
            logging.info('DynamoDB: Unable to insert into S3 bucket' + bucketName)
            return 'DynamoDB: Unable to insert into S3 bucket' + bucketName
        
    if source == 'rds.amazonaws.com':
        logging.info('RDS: This is a rds DeleteDBInstance event')    


        dbInstanceArn = events['responseElements']['dBInstanceArn']
        dbiResourceId = events['responseElements']['dbiResourceId']
        engine = events['responseElements']['engine']
        dbInstanceIdentifier =events['responseElements']['dBInstanceIdentifier']
        #clusterIdentifier = events['responseElements']['clusterIdentifier']

        logging.info("RDS: " + engine +  ": " + dbInstanceArn)
        logging.info('RDS: Sending notification... ')

        isNotificationSent = sendDeleteDBSNSNotification(targetRoleArn, dbInstanceArn, snsTopic, function_name, regions, accountId, dbInstanceIdentifier)
        if isNotificationSent:
            logging.info("RDS:" + engine + ": " +  "Success! Sent message to SNS Topic: " + snsTopic)
        else:
            logging.warning("RDS:" + engine + ": " +  "Fail! Failed to send message to SNS Topic: " + snsTopic)

        deleteStatusFile = Path('/tmp/wdb-inventory_' + dbInstanceIdentifier + '.properties')
        isFileCreated = False
        try:
            open(deleteStatusFile, 'a').close()
            isFileCreated = True
        except IOError as ioe:
            logging.error("RDS: Exception when creating a file: " + str(ioe))
            return "RDS: Unable to create a file"
        
        if isFileCreated:
            logging.info('RDS: deleteStatusFile created successfully')
        else:
            logging.warning('RDS: Failed to create deleteStatusFile')
            return "RDS: Failed to create a file"
         
        keyName = "Anthem-Cloud-Databases/" + dateString + "/" +  accountId + "_" + regions + "_" + engine + "_" + dbInstanceIdentifier + "_deleted.properties"
        isS3WriteSuccessfull = pushToHubS3Bucket(targetRoleArn, deleteStatusFile, keyName, bucketName)
        if isS3WriteSuccessfull != True:
            logging.info("Redshift: Unable to insert into S3 bucket " + bucketName)
            return "Redshift: Unable to insert into S3 bucket " + bucketName
        
    if source == 'redshift.amazonaws.com':
        account_id = events['userIdentity']['accountId']
        engine = 'redshift'
        cluster_identifier = events['requestParameters']['clusterIdentifier']

        logging.info("RDS: Redshift Cluster Identifier:",cluster_identifier)
        logging.info('RDS: Sending notification...')

        isNotificationSent =  sendDeleteDBSNSNotification(targetRoleArn,cluster_identifier, snsTopic, function_name, regions,accountId, cluster_identifier )
        if (isNotificationSent == True):
            logging.info("RDS: Success! Sent message to SNS Topic: " + snsTopic)
        else:
            logging.warning("RDS: Fail! Failed to send message to SNS Topic: " + snsTopic)

        deleteStatusFile = Path('/tmp/wdb-inventory_' + cluster_identifier + '.properties')
        isFileCreated = False

        try:
            open(deleteStatusFile, 'a').close()
            isFileCreated = True
        except IOError as ioe:
            logging.error("RDS: Exception when creating a file: " + str(ioe))
            return "RDS: Unable to create a file"
        
        if isFileCreated:
            logging.info('RDS: deleteStatusFile created successfully')
        else:
            logging.warning('RDS: Failed to create deleteStatusFile')
            return "RDS: Failed to create a file"
         
        keyName = "Anthem-Cloud-Databases/" + dateString + "/" +  accountId + "_" + regions + "_" + engine + "_" + cluster_identifier + "_deleted.properties"
        isS3WriteSuccessfull = pushToHubS3Bucket(targetRoleArn, deleteStatusFile, keyName, bucketName)
        if isS3WriteSuccessfull != True:
            logging.info("Redshift: Unable to insert into S3 bucket " + bucketName)
            return "Redshift: Unable to insert into S3 bucket " + bucketName


    logging.info('============================End processing:===================================')

    return "Success!"
