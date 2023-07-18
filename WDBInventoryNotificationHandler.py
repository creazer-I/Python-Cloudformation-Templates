import json
import boto3
import botocore
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

def sendCreateDBSNSNotification(targetRoleArn, snsTopic, message, *configurationValues):
    sns_topic = snsTopic
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
            
            Subject = ("EH Cloud Database Services Create Notification for "+ value1 +':' + value2  +':' + value3)
            )
    else:
        snsPublishResult = sns_client.publish(
            TopicArn = sns_topic, 
            Message = message,
            Subject =  "EH Cloud Database Services Create Notification")    
        
def writeToFile(inventoryFile, propertiesStringBuffer, logging):
    try:
        inventory_path = Path(inventoryFile)
        with inventory_path.open('w') as file:
            file.write('\n'.join(propertiesStringBuffer))

        return True
    except FileNotFoundError as fnfe:
        logging.info(f"File {inventoryFile} not found: {str(fnfe)}")
        return False

def pushToHubS3Bucket(targetRoleArn, inventoryFile, keyName, logging, bucketName):
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

def isNewRDSInstance(creationTime, currenttime, logging):
    creation_datetime = datetime.strptime(creationTime, '%Y-%m-%d %H:%M:%S')
    current_datetime = datetime.strptime(currenttime, '%Y-%m-%d %H:%M:%S')

    creation_time_in_hours = (current_datetime - creation_datetime) // timedelta(hours=1)

    logging.info("creation_time_in_hours:" +str(creation_time_in_hours))

    if creation_time_in_hours > 2:
        return False
    
    return True

def WDBInventoryNotificationHandler(event, context):    
    
    targetRoleArn =os.environ['targetRoleArn']     
    bucketName =os.environ['targetBucket']
    snsTopic =os.environ['dam_db_status_topic']
    #vpcEndpoint = os.environ['vpc_endpoint']
    regions = os.environ['region']


    system_class_map = {
    'aurora-mysql': 'u_cmdb_ci_db_aurora_mysql_instance',
    'aurora-postgresql': 'u_cmdb_ci_db_aurora_postgresql_instance',
    'docdb': 'u_cmdb_ci_db_docdb_instance',
    'mariadb': 'u_cmdb_ci_db_mariadb_instance',
    'mysql': 'u_cmdb_ci_db_mysql_cloud_instance',
    'neptune': 'u_cmdb_ci_db_neptune_instance',
    'oracle-ee': 'u_cmdb_ci_db_oracle_cloud_instance',
    'postgres': 'u_cmdb_ci_postgresql_cloud_instance',
    'sqlserver-ee': 'u_cmdb_ci_db_mssql_cloud_instance',
    'dynamodb': 'mdb_ci_dynamodb_table',
    'redshift': 'u_cmdb_ci_redshift_instance'
    }


    logging.info('================================== Begin Processing =====================')

    events = event['detail']

    logging.info('Event :', events)

    source = events['eventSource']
    

    if source == None:
        logging.info('source is null')
        return 'null'

    if source != 'rds.amazonaws.com' and source != 'dynamodb.amazonaws.com' and source != 'redshift.amazonaws.com':
        logging.info('Source is ', source, '-- not an RDS or DynamoDB or Redshift event: Exiting')
        return (source,'-- not an RDS or DynamoDB or Redshift event')

    accountId = events['userIdentity']['accountId']

    dateString = datetime.now().strftime('%d%m%Y')

    if source == 'dynamodb.amazonaws.com':
        logging.info('Dynamo DB event')

        eventName = events['eventName']
        if eventName == None:
            logging.info('eventName is null')
            return('Not a DB event')

        if eventName != 'CreateTable':
            logging.info('Not a CreateTable Event') 
            return('Not a createTable event')

        tableName = events['requestParameters']['tableName']

        tableArn = events['responseElements']['tableDescription']['tableArn']

        tableIdentityElement = events['responseElements']['tableDescription']['tableId']

        statusElement = events['responseElements']['tableDescription']['tableStatus']
        
        
        dynamodbclient = boto3.client('dynamodb')

        list_tags = dynamodbclient.list_tags_of_resource(
            ResourceArn=tableArn
        )
        
        
        
        

        dynamoDBPropertiesStringBuffer = []

        dynamoDBPropertiesStringBuffer.append('')
        dynamoDBPropertiesStringBuffer.append('sys_class_name=' + system_class_map.get('dynamodb'))
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_cloud_provider=AWS(Amazon)')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('support_group=Cloud Database Support')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('ip_address=N/A')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_account_id=' + accountId)
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_dbms_version=N/A')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_host_name=')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_instance_name='+ tableName)
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('dns_domain=')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_instance_type=DBMS Instance')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_connection_string=')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('tcp_port=')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_encrypted=')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_database_cluster_identifier=')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_database_name=N/A')
        dynamoDBPropertiesStringBuffer.append('\n')

        dynamoDBPropertiesStringBuffer.append('u_originating_company=Anthem')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_support_model=Outsourced')
        

        tagArray = list_tags['Tags']
        flag1 = False
        flag2 = False
        flag3 = False
        flag4 = False
        flag5 = False
        flag6 = False
        flag7 = False

        for i in tagArray:
            if i['Key'] == 'barometer-it':
                dynamoDBPropertiesStringBuffer.append('u_supported_applications=' + i['Value'])
                dynamoDBPropertiesStringBuffer.append('\n')
                flag1 = True
            if i['Key'] == 'privacy-data':
                dynamoDBPropertiesStringBuffer.append('u_dcc_pr=' + i['Value'])
                dynamoDBPropertiesStringBuffer.append('\n')
                flag2 = True
            if i['Key'] == 'financial-regulatory-data':
                dynamoDBPropertiesStringBuffer.append('u_dcc_fr=' + i['Value'])
                dynamoDBPropertiesStringBuffer.append('\n')
                flag3 = True
            if i['Key'] == 'legal-data':
                dynamoDBPropertiesStringBuffer.append('u_dcc_la=' + i['Value'])
                dynamoDBPropertiesStringBuffer.append('\n')
                flag4 = True
            if i['Key'] == 'financial-internal-data':
                dynamoDBPropertiesStringBuffer.append('u_dcc_fi=' + i['Value'])
                dynamoDBPropertiesStringBuffer.append('\n')
                flag5 = True
            if i['Key'] == 'environment':
                dynamoDBPropertiesStringBuffer.append('u_environment=' + i['Value'])
                dynamoDBPropertiesStringBuffer.append('\n')
                flag6 = True
            if i['Key'] == 'company':
                if i['Value'] == 'antm':
                    companyName = 'Anthem'
                dynamoDBPropertiesStringBuffer.append('u_environment=' + companyName)
                dynamoDBPropertiesStringBuffer.append('\n')
                flag7 = True
            if flag1 and flag2 and flag3 and flag4 and flag5 and flag6 and flag7:
                break    
               
        logging.info('Flags status : ', flag1 and flag2 and flag3 and flag4 and flag5 and flag6 and flag7)

        dynamoDBPropertiesStringBuffer.append('u_dcc_bu=Inherit from Application')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_bcc_rt=Inherit from Application')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_bcc_ac=Inherit from Application')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_network_access_type=Open')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('u_authentication_method=DBMS')
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('Cloud Details: Configuration Table ARN=' + tableArn[8:])
        dynamoDBPropertiesStringBuffer.append('\n')
        
        seStatus=statusElement
        if seStatus == 'ENABLED':
            seStatus = 'TRUE'
        else:
            seStatus = 'FALSE'
        dynamoDBPropertiesStringBuffer.append('Cloud Details: Configuration SSE Description Status='+ statusElement)
        dynamoDBPropertiesStringBuffer.append('\n')
        dynamoDBPropertiesStringBuffer.append('Cloud Details: Configuration table name=' + tableName)
        dynamoDBPropertiesStringBuffer.append('\n')

        logging.info('---------------------- DynamoDB Properties Start ---------------------------')
        logging.info(dynamoDBPropertiesStringBuffer)
        logging.info('---------------------- DynamoDB Properties End -----------------------------')
    
        logging.info('DynamoDB : Sending Notification')
        message = []
        message.append('The following Database has just been created')
        message.append('\n')
        message.append('\n')
        message.append('ARN: ' + tableArn)
        message.append('\n')
        message.append('\n')
        message.append('===================Properties===========================')
        message.append('\n')
        message.append(''.join(dynamoDBPropertiesStringBuffer))
        message.append('\r\n')
        message.append('\r\n')
        message.append('PS. This message is being sent from the function: ' + context.function_name + ' to the topic: ' + snsTopic +  '\n')

        isNotificationSent =  sendCreateDBSNSNotification(targetRoleArn, snsTopic, message, logging, regions,accountId, tableName )
        if (isNotificationSent == True):
            logging.info('DynamoDB: Success')
        else:
            logging.info('DynamoDB: Fail')


        inventoryFile = Path('/tmp/wdb-inventory_' + tableName + '.properties')

        isFileWriteSuccess = writeToFile(inventoryFile, dynamoDBPropertiesStringBuffer, logging)
        if isFileWriteSuccess != True:
            logging.info('DynamoDB: Unable to write to file /tmp/wdb-inventory.properties')
            return 'DynamoDB: Unable to write to file /tmp/wdb-inventory.properties'
        
        keyName = "Anthem-Cloud-Databases/" + dateString + "/" +  accountId + "_" + regions + "_" + "dynamodb" + "_" + tableIdentityElement + "_" + tableName + "_created.properties"

        isS3WriteSuccessfull = pushToHubS3Bucket(targetRoleArn, inventoryFile, keyName, logging, bucketName)
        print(isS3WriteSuccessfull)
        if isS3WriteSuccessfull != True:
            logging.info('DynamoDB: Unable to insert into S3 bucket ' + bucketName)
            return 'DynamoDB: Unable to insert into S3 bucket ' + bucketName
        
##DyanmoDB end        
        
    elif source == 'rds.amazonaws.com':
        eventID = events["eventID"]
        
        if eventID == None:
            logging.info('eventID is null/not present: Exiting')
            return 'eventID is null/not present'
        
        logging.info('EventIdString' + eventID)

        if eventID != 'RDS-EVENT-0005' and eventID != 'RDS-EVENT-0001' and eventID != 'RDS-EVENT-0046':
            logging.info('Not an RDS create/backup/read replica event: Exiting')
            return 'Not an RDS create/backup/read replica event'
        
        sourceID = events['requestParameters']['dBInstanceIdentifier']

        rdsClient = boto3.client('rds')
            
        describeInstance = rdsClient.describe_db_instances(
            DBInstanceIdentifier=sourceID,
        )
        print(eventID)
        ######################remove testing ########################
        
        #dbInstances = events

        dbInstances = describeInstance['DBInstances'][0]

        if dbInstances == None:
            logging.info(sourceID + 'Instance is not found!')
            return "Failed: " + sourceID + 'Instance is not found!'
        
        dbiResourceID = dbInstances['DbiResourceId']
        engine = dbInstances['Engine']
        engineVersion = dbInstances['EngineVersion']

        if (engine.startswith('oracle') or engine.startswith('mysql') or engine.startswith('postgres') or engine.startswith("sqlserver")) and eventID == "RDS-EVENT-0005" :
            logging.info('RDS Engine: ' + engine  + ' -- Event 0005 -- create--full metadata is not available: Exiting')
            return 'RDS Engine: ' + engine  + ' -- Event 0005 -- create--full metadata is not available'
    
        if (engine.startswith('oracle') or engine.startswith('mysql') or engine.startswith('postgres') or engine.startswith("sqlserver")) and eventID == "RDS-EVENT-0001" :
            rdsInstanceCreateTime = dbInstances['InstanceCreateTime']
            
            if isNewRDSInstance(rdsInstanceCreateTime, datetime.now(), logging) != True:
                logging.info('An existing RDS Instance ' + dbInstances['DBInstanceIdentifier']    + ' is being backed up')
                return 'An existing RDS Instance' + dbInstances['DBInstanceIdentifier']  + 'is being backed up' 
        
        rds_list_tags = dbInstances['TagList']
        
        databaseMetadataStringBuffer = []
        databaseMetadataStringBuffer.append('')
        databaseMetadataStringBuffer.append("sys_class_name=" + system_class_map.get(engine))
        databaseMetadataStringBuffer.append("\n")
        databaseMetadataStringBuffer.append("u_cloud_provider=AWS (Amazon)")
        databaseMetadataStringBuffer.append("\n")
        databaseMetadataStringBuffer.append("support_group=Cloud Database Support")
        databaseMetadataStringBuffer.append("\n")
        databaseMetadataStringBuffer.append("ip_address=N/A")
        databaseMetadataStringBuffer.append("\n")
        databaseMetadataStringBuffer.append("u_account_id=" + accountId)
        databaseMetadataStringBuffer.append("\n")
        databaseMetadataStringBuffer.append("u_dbms_version=" + engineVersion)
        databaseMetadataStringBuffer.append("\n")

        dbCluster = None
        if engine == 'aurora-mysql' or engine == 'aurora-postgresql' or engine == 'docdb' or engine == 'neptune':
            clusterIdentifier = dbInstances['DBClusterIdentifier']
            databaseIdentifier = clusterIdentifier

            dbClusterRequest = rdsClient.describe_db_clusters(
                                    DBClusterIdentifier=databaseIdentifier
                                )
            
            dbClusterResult = dbClusterRequest['DBClusters'][0]

            if dbCluster == None:
                logging.info(engine, "DB Cluster is null!")
                return engine ," clusterIdentifier + " , " is not found"
            
            databaseMetadataStringBuffer.append("u_host_name=", dbCluster['Endpoint'])
            databaseMetadataStringBuffer.append("\n")
            databaseMetadataStringBuffer.append("tcp_port=", dbCluster['Port'])
            databaseMetadataStringBuffer.append("\n")
            databaseMetadataStringBuffer.append("u_encrypted=",dbCluster['StorageEncrypted'])
            databaseMetadataStringBuffer.append("\n")

        else:
            databaseIdentifier = dbInstances['DBInstanceIdentifier']

            endpoint = dbInstances['Endpoint']
            address = None
            port = None

            if endpoint != None:
                address = endpoint['Address']
                port = str(endpoint['Port'])

            databaseMetadataStringBuffer.append("u_host_name=" + address)
            databaseMetadataStringBuffer.append("\n")
            databaseMetadataStringBuffer.append("tcp_port="+ port)
            databaseMetadataStringBuffer.append("\n")

            connectionString = None

            if engine.startswith("oracle") and address != None and port != None:
                connectionString = dbInstances['DBName'] + "=(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=" +  address + ")(PORT=" + port + ")))(CONNECT_DATA=(SERVICE_NAME=" + dbInstances['DBName'] + ")))"

                databaseMetadataStringBuffer.append("u_connection_string="+ str(connectionString))
                databaseMetadataStringBuffer.append("\n")
                databaseMetadataStringBuffer.append("u_encrypted="+ dbInstances['StorageEncrypted'])
                databaseMetadataStringBuffer.append("\n")


                databaseMetadataStringBuffer.append("u_instance_name="+ dbInstances['DBInstanceIdentifier'])
                databaseMetadataStringBuffer.append("\n")
                databaseMetadataStringBuffer.append("dns_domain=rds.amazonaws.com")
                databaseMetadataStringBuffer.append("\n")
                databaseMetadataStringBuffer.append("u_instance_type=DBMS Instance")
                databaseMetadataStringBuffer.append("\n")
                        
                        
                databaseMetadataStringBuffer.append("u_database_cluster_identifier="+ clusterIdentifier)
                databaseMetadataStringBuffer.append("\n")
                databaseMetadataStringBuffer.append("u_database_name="+ dbInstances['DBName'])
                databaseMetadataStringBuffer.append("\n")
                databaseMetadataStringBuffer.append("u_support_model=Outsourced")
                databaseMetadataStringBuffer.append("\n")

        logging.info("TagList=", rds_list_tags)

        flag1 = False
        flag2 = False
        flag3 = False
        flag4 = False
        flag5 = False
        flag6 = False
        flag7 = False

        for i in rds_list_tags:
            if i['Key'] == 'barometer-it':
                databaseMetadataStringBuffer.append('u_supported_applications=' + i['Value'])
                databaseMetadataStringBuffer.append('\n')
                flag1 = True
            if i['Key'] == 'privacy-data':
                databaseMetadataStringBuffer.append('u_dcc_pr=' + i['Value'])
                databaseMetadataStringBuffer.append('\n')
                flag2 = True
            if i['Key'] == 'financial-regulatory-data':
                databaseMetadataStringBuffer.append('u_dcc_fr=' + i['Value'])
                databaseMetadataStringBuffer.append('\n')
                flag3 = True
            if i['Key'] == 'legal-data':
                databaseMetadataStringBuffer.append('u_dcc_la=' + i['Value'])
                databaseMetadataStringBuffer.append('\n')
                flag4 = True
            if i['Key'] == 'financial-internal-data':
                databaseMetadataStringBuffer.append('u_dcc_fi=' + i['Value'])
                databaseMetadataStringBuffer.append('\n')
                flag5 = True
            if i['Key'] == 'environment':
                databaseMetadataStringBuffer.append('u_environment=' + i['Value'])
                databaseMetadataStringBuffer.append('\n')
                flag6 = True
            if i['Key'] == 'company':
                if i['Value'] == 'antm':
                    companyName = 'Anthem'
                databaseMetadataStringBuffer.append('u_environment=' + companyName)
                databaseMetadataStringBuffer.append('\n')
                flag7 = True
            if flag1 and flag2 and flag3 and flag4 and flag5 and flag6 and flag7:
                break   

        logging.info('Flags status : ', flag1 and flag2 and flag3 and flag4 and flag5 and flag6 and flag7)

        databaseMetadataStringBuffer.append('u_dcc_bu=Inherit from Application')
        databaseMetadataStringBuffer.append('\n')
        databaseMetadataStringBuffer.append('u_bcc_rt=Inherit from Application')
        databaseMetadataStringBuffer.append('\n')
        databaseMetadataStringBuffer.append('u_bcc_ac=Inherit from Application')
        databaseMetadataStringBuffer.append('\n')
        databaseMetadataStringBuffer.append('u_network_access_type=Open')
        databaseMetadataStringBuffer.append('\n')
        databaseMetadataStringBuffer.append('u_authentication_method=DBMS')
        databaseMetadataStringBuffer.append('\n')


        
        logging.info('---------------------- ' ,engine, ' Start ---------------------------')
        logging.info(databaseMetadataStringBuffer)
        logging.info('---------------------- ' ,engine, ' End -----------------------------')


        logging.info('Prepare Message')

        message = []
        message.append('The following Database has just been created')
        message.append('\n')
        message.append('\n')
        message.append('ARN: ' + dbInstances['DBInstanceArn'])
        message.append('\n')
        message.append('\n')
        message.append('===================Properties===========================')
        message.append('\n')
        message.append(''.join(databaseMetadataStringBuffer))
        message.append('\r\n')
        message.append('\r\n')
        message.append('PS. This message is being sent from the function: ' + context.function_name + ' to the topic: ' + snsTopic)

        logging.info(engine, ": Sending notification ...")
        
        isNotificationSentRds = sendCreateDBSNSNotification(sendCreateDBSNSNotification, snsTopic, message, logging, regions, accountId, dbInstances['DBInstanceIdentifier'])
        if isNotificationSentRds:
            logging.info(engine + ": Success! Sent message to SNS Topic: " + snsTopic)
        else:
            logging.info(engine + ": Fail! Failed to send message to SNS Topic: " + snsTopic)

        inventoryFile = Path("/tmp/wdb-inventory_" + dbInstances['DBInstanceIdentifier']+ ".properties")
        isFileWriteSuccess = writeToFile(inventoryFile, databaseMetadataStringBuffer, logging)
        if isFileWriteSuccess == False:
            logging.info(engine + ": Unable to write to file /tmp/wdb-inventory.properties")
            return engine + ": Unable to write to file /tmp/wdb-inventory.properties"
        
        keyName = "Anthem-Cloud-Databases/" + dateString + "/" + accountId + "_" + regions + "_" + engine + "_" + dbiResourceID + "_" + dbInstances['DBInstanceIdentifier'] + "_created.properties"

        isS3WriteSuccessfull = pushToHubS3Bucket(targetRoleArn, inventoryFile, keyName, logging, bucketName)
        if isS3WriteSuccessfull == False:
                logging.info(engine + ": Unable to insert into S3 bucket " + bucketName)
                return engine + ": Unable to insert into S3 bucket " + bucketName
            
    elif source == 'redshift.amazonaws.com':
        logging.info('--------------------------This is a Redshift event--------------------------------')
        eventName = events['eventName']
        if eventName == None:
            logging.info('eventName is null/not present: Exiting ')
            return('Eventname is empty; Not a Redshift Event')

        if eventName != 'CreateCluster':
            logging.info('Not a Redshift CreateTable  Event') 
            return('Not a Redshift CreateCluster Event')
        
        requestParametersClusterElement = events['requestParameters']['clusterIdentifier']

        redshiftClient = boto3.client('redshift')

        describeClustersRequests = redshiftClient.describe_clusters(
                                        ClusterIdentifier= requestParametersClusterElement
                                    )
        redshiftCluster = describeClustersRequests['Clusters'][0]

        engine = "redshift"
    
        
        redshiftProperties = []
        endpoint = redshiftCluster['Endpoint']

        if endpoint != None:
            address = endpoint['Address']
            port    = str(endpoint['Port'])

            redshiftProperties.append("u_host_name=" + address)
            redshiftProperties.append("\n")
            redshiftProperties.append("tcp_port=" + port)
            redshiftProperties.append("\n")

        redshiftProperties.append("")
        redshiftProperties.append("sys_class_name=" + system_class_map.get("redshift"))
        redshiftProperties.append("\n")
        redshiftProperties.append("u_cloud_provider=AWS(Amazon)")
        redshiftProperties.append("\n")
        redshiftProperties.append("support_group=Cloud Database Support")
        redshiftProperties.append("\n")
        redshiftProperties.append("ip_address=N/A")
        redshiftProperties.append("\n")
        redshiftProperties.append("u_account_id=" + accountId)
        redshiftProperties.append("\n")
        redshiftProperties.append("u_dbms_version=N/A")
        redshiftProperties.append("\n")
        redshiftProperties.append("u_instance_name=" + redshiftCluster['DBName'])
        redshiftProperties.append("\n")
        redshiftProperties.append("dns_domain=redshift.amazonaws.com")
        redshiftProperties.append("\n")
        redshiftProperties.append("u_instance_type=DBMS Instance")
        redshiftProperties.append("\n")
        redshiftProperties.append("u_connection_string=")
        redshiftProperties.append("\n")
        redshiftProperties.append("u_encrypted=" + str(redshiftCluster['Encrypted']))
        redshiftProperties.append("\n")
        redshiftProperties.append("u_database_cluster_identifier=" + redshiftCluster['ClusterIdentifier'])
        redshiftProperties.append("\n")
        redshiftProperties.append("u_database_name=" + redshiftCluster['DBName'])
        redshiftProperties.append("\n")

        redshiftProperties.append("u_originating_company=Anthem")
        redshiftProperties.append("\n")
        redshiftProperties.append("u_support_model=Outsourced")
        redshiftProperties.append("\n")

        taglist = redshiftCluster['Tags']
        flag1 = False
        flag2 = False
        flag3 = False
        flag4 = False
        flag5 = False
        flag6 = False
        flag7 = False
        
        for i in taglist:
            for Key, Value in i.items():
                if i['Key'] == 'barometer-it':
                    redshiftProperties.append('u_supported_applications=' + i['Value'])
                    redshiftProperties.append('\n')
                    flag1 = True
                if i['Key'] == 'privacy-data':
                    redshiftProperties.append('u_dcc_pr=' + i['Value'])
                    redshiftProperties.append('\n')
                    flag2 = True
                if i['Key'] == 'financial-regulatory-data':
                    redshiftProperties.append('u_dcc_fr=' + i['Value'])
                    redshiftProperties.append('\n')
                    flag3 = True
                if i['Key'] == 'legal-data':
                    redshiftProperties.append('u_dcc_la=' + i['Value'])
                    redshiftProperties.append('\n')
                    flag4 = True
                if i['Key'] == 'financial-internal-data':
                    redshiftProperties.append('u_dcc_fi=' + i['Value'])
                    redshiftProperties.append('\n')
                    flag5 = True
                if i['Key'] == 'environment':
                    redshiftProperties.append('u_environment=' + i['Value'])
                    redshiftProperties.append('\n')
                    flag6 = True
                if i['Key'] == 'company':
                    if i['Value'] == 'antm':
                        companyName = 'Anthem'
                    redshiftProperties.append('u_environment=' + companyName)
                    redshiftProperties.append('\n')
                    flag7 = True
                if flag1 and flag2 and flag3 and flag4 and flag5 and flag6 and flag7:
                    break   
                
        logging.info('Flags status : ', flag1 and flag2 and flag3 and flag4 and flag5 and flag6 and flag7)

        redshiftProperties.append('u_dcc_bu=Inherit from Application')
        redshiftProperties.append('\n')
        redshiftProperties.append('u_bcc_rt=Inherit from Application')
        redshiftProperties.append('\n')
        redshiftProperties.append('u_bcc_ac=Inherit from Application')
        redshiftProperties.append('\n')
        redshiftProperties.append('u_network_access_type=Open')
        redshiftProperties.append('\n')
        redshiftProperties.append('u_authentication_method=DBMS')
        redshiftProperties.append('\n')
        
        logging.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$ Redshift Properties Start $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        logging.info(redshiftProperties)
        logging.info("$$$$$$$$$$$$$$$$$$$$$$$$$$ Redshift Properties End $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

        logging.info("Prepare message ")

        message= []
        message.append('The following Database has just been created')
        message.append('\n')
        message.append('\n')
        message.append('ARN: ' + redshiftCluster['ClusterNamespaceArn'])
        message.append('\n')
        message.append('\n')
        message.append('===================Properties===========================')
        message.append('\n')
        message.append(''.join(redshiftProperties))
        message.append('\r\n')
        message.append('\r\n')
        message.append('PS. This message is being sent from the function: ' + context.function_name + ' to the topic: ' + snsTopic +  '\n')

        logging.info(engine , ": Sending notification...")
        isNotificationSent = sendCreateDBSNSNotification(sendCreateDBSNSNotification, snsTopic, message, logging, regions, accountId, redshiftCluster['ClusterIdentifier'])

        if isNotificationSent == True:
            logging.info(engine , ": Success! Sent message to SNS Topic: " , snsTopic)
        else:
            logging.info(engine , ": Fail! Failed to send message to SNS Topic: " , snsTopic)

        
        inventoryFile = Path("/tmp/wdb-inventory_" + redshiftCluster['ClusterIdentifier'] + ".properties")
        isFileWriteSuccess = writeToFile(inventoryFile, redshiftProperties, logging)
        if isFileWriteSuccess == False:
            logging.info(engine + ": Unable to write to file /tmp/wdb-inventory.properties")
            return engine + ": Unable to write to file /tmp/wdb-inventory.properties"


        keyName = "Anthem-Cloud-Databases/" + dateString + "/" + accountId + "_" + regions + "_" + engine + "_" + redshiftCluster['ClusterIdentifier'] + "_created.properties"

        isS3WriteSuccessfull = pushToHubS3Bucket(targetRoleArn, inventoryFile, keyName, logging, bucketName)
        if isS3WriteSuccessfull == False:
                logging.info(engine + ": Unable to insert into S3 bucket " + bucketName)
                return engine + ": Unable to insert into S3 bucket " + bucketName
        

    else:
        logging.info("This is not an RDS or DynamoDB or Redshift event")
        return "This is not an RDS or DynamoDB or Redshift event"
    

    return "Success"







