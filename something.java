package com.anthem.lambda;


import java.io.File;
import java.io.FileNotFoundException;
import java.io.PrintWriter;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Calendar;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.amazonaws.AmazonServiceException;
import com.amazonaws.auth.AWSStaticCredentialsProvider;
import com.amazonaws.auth.BasicSessionCredentials;
import com.amazonaws.client.builder.AwsClientBuilder;
import com.amazonaws.client.builder.AwsClientBuilder.EndpointConfiguration;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDB;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClientBuilder;
import com.amazonaws.services.dynamodbv2.model.ListTagsOfResourceRequest;
import com.amazonaws.services.dynamodbv2.model.ListTagsOfResourceResult;
import com.amazonaws.services.dynamodbv2.model.Tag;
import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.rds.AmazonRDS;
import com.amazonaws.services.rds.AmazonRDSClientBuilder;
import com.amazonaws.services.rds.model.DBCluster;
import com.amazonaws.services.rds.model.DBInstance;
import com.amazonaws.services.rds.model.DescribeDBClustersRequest;
import com.amazonaws.services.rds.model.DescribeDBClustersResult;
import com.amazonaws.services.rds.model.DescribeDBInstancesResult;
import com.amazonaws.services.rds.model.DescribeDBInstancesRequest;
import com.amazonaws.services.rds.model.Endpoint;
import com.amazonaws.services.redshift.AmazonRedshift;
import com.amazonaws.services.redshift.AmazonRedshiftClientBuilder;
import com.amazonaws.services.redshift.model.Cluster;
import com.amazonaws.services.redshift.model.DescribeClustersRequest;
import com.amazonaws.services.redshift.model.DescribeClustersResult;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3ClientBuilder;
import com.amazonaws.services.s3.model.PutObjectResult;
import com.amazonaws.services.securitytoken.AWSSecurityTokenService;
import com.amazonaws.services.securitytoken.AWSSecurityTokenServiceClientBuilder;
import com.amazonaws.services.securitytoken.model.AssumeRoleRequest;
import com.amazonaws.services.securitytoken.model.AssumeRoleResult;
import com.amazonaws.services.securitytoken.model.Credentials;
import com.amazonaws.services.sns.AmazonSNS;
import com.amazonaws.services.sns.AmazonSNSClientBuilder;
import com.amazonaws.services.sns.model.PublishResult;



public class WDBInventoryNotificationHandler implements RequestHandler<Map<String,Object>, String> {

	Gson gson = new GsonBuilder().setPrettyPrinting().create();
	final String region = System.getenv("AWS_REGION");
	final String targetRoleArn =  System.getenv("targetRoleArn");      
    final String bucketName = System.getenv("targetBucket");
    final String snsTopic = System.getenv("dam_db_status_topic");
    final String vpcEndpoint = System.getenv("vpc_endpoint");
    
    Map<String,String> systemClassMap = new HashMap<String,String>();
    
    {
    	systemClassMap.put("aurora-mysql", "u_cmdb_ci_db_aurora_mysql_instance");
    	systemClassMap.put("aurora-postgresql", "u_cmdb_ci_db_aurora_postgresql_instance");
    	systemClassMap.put("docdb", "u_cmdb_ci_db_docdb_instance");
    	systemClassMap.put("mariadb", "u_cmdb_ci_db_mariadb_instance");
    	systemClassMap.put("mysql", "u_cmdb_ci_db_mysql_cloud_instance");
    	systemClassMap.put("neptune", "u_cmdb_ci_db_neptune_instance");
    	systemClassMap.put("oracle-ee", "u_cmdb_ci_db_oracle_cloud_instance");
    	systemClassMap.put("postgres", "u_cmdb_ci_postgresql_cloud_instance");
    	systemClassMap.put("sqlserver-ee", "u_cmdb_ci_db_aurora_postgresql_instance");
    	systemClassMap.put("sqlserver-ee", "u_cmdb_ci_db_mssql_cloud_instance");
    	systemClassMap.put("dynamodb", "mdb_ci_dynamodb_table");
    	systemClassMap.put("redshift", "u_cmdb_ci_redshift_instance");
    	
    }
	
	   @Override
	   
	   public String handleRequest(Map<String,Object> event, Context context) {
		    
		   
		    LambdaLogger logger = context.getLogger();
		    
		    logger.log("============================Begin processing:=================================== " + System.currentTimeMillis());
	    
		    String jsonEventString = gson.toJson(event);
		    
		    logger.log("EVENT: " + jsonEventString);
		    
		    
		    //convert the event json string to a json object
		    JsonObject eventJsonObject = JsonParser.parseString(jsonEventString).getAsJsonObject();
		    
		    //First determine if this is a DynamoDB event or an RDS event
		    
		    JsonElement sourceJsonElement = (eventJsonObject.get("source"));
		    
		    if (sourceJsonElement == null){
		    	logger.log("source is null/not present: Not an RDS or DynamoDB event: Exiting ");
		    	return "source is null/not present: Not an RDS or DynamoDB event";
		    }
		    
		    String source = sourceJsonElement.getAsString();
		    
		    if (!source.equalsIgnoreCase("aws.rds") && !source.equalsIgnoreCase("aws.dynamodb")
		    		&& !source.equalsIgnoreCase("aws.redshift")){
		    	logger.log("source is " + source + " -- not an RDS or DynamoDB or Redshift event: Exiting");
		    	return "source is "  + source + " -- not an RDS or DynamoDB or Redshift event";
		    }
		    
		    JsonElement accountJsonElement = (eventJsonObject.get("account"));
		    String accountId = accountJsonElement.getAsString();
		    
		    //Keyname prefix ddmmyyyy
		    DateTimeFormatter dtf = DateTimeFormatter.ofPattern("ddMMyyyy");
	    	LocalDate localDate = LocalDate.now();
	    	String dateString = dtf.format(localDate);
		    
		    
            if (source.equalsIgnoreCase("aws.dynamodb")){
            	
            	//DynamoDB -- needs a client of its own
		    	logger.log("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@This is a DynamoDB event@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@");
		    	
		    	JsonElement eventNameJsonElement = (eventJsonObject.getAsJsonObject("detail")).get("eventName");
			    if (eventNameJsonElement == null){
			    	logger.log("eventName is null/not present: Exiting ");
			    	return "Not a DynamoDB/MySQL/Oracle/MariaDB/Neptune/SQLServer/Aurora-PostGres/DocumentDB Event";
			    }
		    	
		    	String eventName = eventNameJsonElement.getAsString();
			    
		    	if ( !(eventName.equalsIgnoreCase("CreateTable") ) ){
			    	logger.log("Not a DynamoDB CreateTable Event");
			    	return "Not a DynamoDB CreateTable Event";
			    }
		    	
		    	JsonElement requestParametersElement = eventJsonObject.getAsJsonObject("detail").getAsJsonObject("requestParameters").get("tableName");
			    String tableName = requestParametersElement.getAsString();
			    
			    JsonElement tableArnElement = eventJsonObject.getAsJsonObject("detail").getAsJsonObject("responseElements")
			    		             .getAsJsonObject("tableDescription").get("tableArn");
			    String tableArnName = tableArnElement.getAsString();
			    
			    JsonElement tableIdentityElement = eventJsonObject.getAsJsonObject("detail").getAsJsonObject("responseElements")
   		             .getAsJsonObject("tableDescription").get("tableId");
                String tableId = tableIdentityElement.getAsString();
			    
			    JsonElement sseStatusElement = eventJsonObject.getAsJsonObject("detail").getAsJsonObject("responseElements")
   		             .getAsJsonObject("tableDescription").getAsJsonObject("sSEDescription").get("status");
			    
		    	
		    	final AmazonDynamoDB dynamodbClient = AmazonDynamoDBClientBuilder.defaultClient();
			    ListTagsOfResourceRequest listTagsOfResourceRequest = new ListTagsOfResourceRequest().withResourceArn(tableArnName);
			    ListTagsOfResourceResult listTagsOfResourceResult = dynamodbClient.listTagsOfResource(listTagsOfResourceRequest);
			    List<com.amazonaws.services.dynamodbv2.model.Tag> tagList =  listTagsOfResourceResult.getTags();
			    
			    StringBuffer dynamoDBPropertiesStringBuffer = new StringBuffer();
			    dynamoDBPropertiesStringBuffer.append("");
			    dynamoDBPropertiesStringBuffer.append("sys_class_name=").append(systemClassMap.get("dynamodb"));
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_cloud_provider=").append("AWS(Amazon)");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("support_group=").append("Cloud Database Support");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("ip_address=").append("N/A");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_account_id=").append(accountId);
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_dbms_version=").append("N/A");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_host_name=").append("");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_instance_name=").append(tableName);
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("dns_domain=").append("");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_instance_type=").append("DBMS Instance");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_connection_string=").append("");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("tcp_port=").append("");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_encrypted=").append("");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_database_cluster_identifier=").append("");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_database_name=").append("N/A");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    
			    
			    
			    dynamoDBPropertiesStringBuffer.append("u_originating_company=").append("Anthem");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_support_model=").append("Outsourced");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    
			    int tagArrayLength = tagList.size();
			    boolean flag1 = false,flag2=false,flag3=false,flag4=false,flag5=false,flag6 = false, flag7 = false;
			    
			    		    
			    for (int i=0; i< tagArrayLength;i++){
			    	Tag rdsTag = tagList.get(i);
			    	
			    	if (rdsTag.getKey().equalsIgnoreCase("barometer-it")){
			    		dynamoDBPropertiesStringBuffer.append("u_supported_applications=").append(rdsTag.getValue()).append("\n");
			    		flag1 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("privacy-data")){
			    		dynamoDBPropertiesStringBuffer.append("u_dcc_pr=").append(rdsTag.getValue()).append("\n");
			    		flag2 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("financial-regulatory-data")){
			    		dynamoDBPropertiesStringBuffer.append("u_dcc_fr=").append(rdsTag.getValue()).append("\n");
			    		flag3 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("legal-data")){
			    		dynamoDBPropertiesStringBuffer.append("u_dcc_la=").append(rdsTag.getValue()).append("\n");
			    		flag4 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("financial-internal-data")){
			    		dynamoDBPropertiesStringBuffer.append("u_dcc_fi=").append(rdsTag.getValue()).append("\n");
			    		flag5 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("environment")){
			    		dynamoDBPropertiesStringBuffer.append("u_environment=").append(rdsTag.getValue()).append("\n");
			    		flag6 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("company")){
			    		String companyName = rdsTag.getValue();
			    		if (companyName.equalsIgnoreCase("antm")){
			    			companyName = "Anthem";
			    		}
			    		dynamoDBPropertiesStringBuffer.append("u_environment=").append(companyName).append("\n");
			    		flag7 = true;
			    	}
			    	if (flag1 && flag2 && flag3 && flag4 && flag5 && flag6 && flag7){
			    		break;
			    	}
			    	
			    }
			    
			    logger.log("Flags status : " + (flag1 && flag2 && flag3 && flag4 && flag5 && flag6 && flag7));
			  
			    dynamoDBPropertiesStringBuffer.append("u_dcc_bu=").append("Inherit from Application");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_bcc_rt=").append("Inherit from Application");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_bcc_ac=").append("Inherit from Application");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_network_access_type=").append("Open");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("u_authentication_method=").append("DBMS");
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("Cloud Details: Configuration Table ARN=").append(tableArnName.substring(8));
			    dynamoDBPropertiesStringBuffer.append("\n"); 
			    String seStatus = sseStatusElement.getAsString();
			    if (seStatus.equalsIgnoreCase("ENABLED")){
			    	seStatus = "TRUE";
			    } else {
			    	seStatus = "FALSE";
			    }
			    dynamoDBPropertiesStringBuffer.append("Cloud Details: Configuration SSE Description Status=").append(sseStatusElement.getAsString());
			    dynamoDBPropertiesStringBuffer.append("\n");
			    dynamoDBPropertiesStringBuffer.append("Cloud Details: Configuration table name=").append(tableName);
			    dynamoDBPropertiesStringBuffer.append("\n");
			    
			    
			    logger.log("$$$$$$$$$$$$$$$$$$$$$$$$$$$ DynamoDB Properties Start $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
			    logger.log(dynamoDBPropertiesStringBuffer.toString());
			    logger.log("$$$$$$$$$$$$$$$$$$$$$$$$$$$ DynamoDB Properties End $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
			    
			    
			    
			    logger.log("DynamoDB: Sending notification... ");
			    StringBuffer message = new StringBuffer();
			    message.append("The following Database has just been created");
			    message.append("\n");
			    message.append("\n");
			    message.append("ARN: " + tableArnName);
			    message.append("\n");
			    message.append("\n");
			    message.append("===================Properties===========================");
			    message.append("\n");
			    message.append(dynamoDBPropertiesStringBuffer.toString());
			    message.append("\r\n");
			    message.append("\r\n");
			    message.append("PS. This message is being sent from the function: " + context.getFunctionName() + " to the topic: " + snsTopic +  "\n");
			    
			    
			    
			    
			    boolean isNotificationSent = sendCreateDBSNSNotification(message.toString(),  logger, region, accountId, tableName);
			    if (isNotificationSent == true){
			    	logger.log("DynamoDB: Success! Sent message to SNS Topic: " + snsTopic);
			    }else {
			    	logger.log("DynamoDB: Fail! Failed to send message to SNS Topic: " + snsTopic);
			    }
			    
			    
			    //Now write to a file
			    File inventoryFile = new File("/tmp/wdb-inventory_" + tableName + ".properties");
			    boolean isFileWriteSuccessful = writeToFile(inventoryFile, dynamoDBPropertiesStringBuffer, logger);
			    if (!isFileWriteSuccessful){
			    	logger.log("DynamoDB: Unable to write to file /tmp/wdb-inventory.properties");
			    	return "DynamoDB: Unable to write to file /tmp/wdb-inventory.properties";
			    }
			    
			    String keyName = "Anthem-Cloud-Databases/" + dateString + "/" +  accountId + "_" + region + "_" + "dynamodb" + "_" + tableId + "_" + tableName + "_created.properties";
			    
			    boolean isS3WriteSuccessful = pushToHubS3Bucket(inventoryFile, keyName, logger);
			    if (!isS3WriteSuccessful){
			    	logger.log("DynamoDB: Unable to insert into S3 bucket " + bucketName);
			    	return "DynamoDB: Unable to insert into S3 bucket " + bucketName;
			    }
			    
			    
			     
            	
            	
            }
            
            else if (source.equalsIgnoreCase("aws.rds")) {
            	
            	JsonElement eventDetailEventIdJsonElement = (eventJsonObject.getAsJsonObject("detail")).get("EventID");
    		    if (eventDetailEventIdJsonElement == null){
    		    	logger.log("eventID is null/not present: Exiting ");
    		    	return "eventID is null/not present";
    		    }
    		    String eventIdString = eventDetailEventIdJsonElement.getAsString();
    		    logger.log("EventIdString: " + eventIdString);
    		    
    		    if (!eventIdString.equalsIgnoreCase("RDS-EVENT-0005") && !eventIdString.equalsIgnoreCase("RDS-EVENT-0001")
    		    		&& !(eventIdString.equalsIgnoreCase("RDS-EVENT-0046"))){
    		    	logger.log("Not an RDS create/backup/read replica event: Exiting ");
    		    	return "Not an RDS create/backup/read replica event";
    		    }
    		    
    		    
    		    
    		    //Get the sourceIdentifier (database name)
    		    JsonElement sourceIdentifierJsonElement = (eventJsonObject.getAsJsonObject("detail")).get("SourceIdentifier");
    		    
    		    AmazonRDS rdsClient = AmazonRDSClientBuilder.defaultClient();
    		    
    		    DescribeDBInstancesRequest dbInstanceRequest = new DescribeDBInstancesRequest();
    		    dbInstanceRequest.setDBInstanceIdentifier(sourceIdentifierJsonElement.getAsString());
    		    
    		    DescribeDBInstancesResult databaseInstanceResponse = rdsClient.describeDBInstances(dbInstanceRequest);
    		    DBInstance dbInstance = databaseInstanceResponse.getDBInstances().get(0);
    		    if (dbInstance == null){
    		    	logger.log( sourceIdentifierJsonElement + " Instance is not found!");
    		    	return "Failed: " + sourceIdentifierJsonElement + " Instance is not found!"; 
    		    }
    		    
    		    String dbiResourceId = dbInstance.getDbiResourceId();
    		    
    		    String engine = dbInstance.getEngine();
    		    String databaseIdentifier = ""; // applies to noth cluster as well as RDS
    		    
    		    if ((engine.startsWith("oracle") || engine.startsWith("mysql") || engine.startsWith("postgres")
    		    		|| engine.startsWith("sqlserver")) && eventIdString.equalsIgnoreCase("RDS-EVENT-0005")){
    		    	logger.log("RDS Engine: " + engine  + " -- Event 0005 -- create--full metadata is not available: Exiting");
    		    	return "RDS Engine: " + engine  + " -- Event 0005 -- create--full metadata is not available";
    		    }
    		    
    		    if ((engine.startsWith("oracle") || engine.startsWith("mysql") || engine.startsWith("postgres")
    		    		|| engine.startsWith("sqlserver")) && (eventIdString.equalsIgnoreCase("RDS-EVENT-0001"))){
    		    	
    		    	//Check if this 0001 backup event is part of a creation, or if it is for an older existing RDS
    		    	//Now check if the backup time (the current time , that is, is less than or equal to 2 hours from the creation time
    		    	Date rdsInstanceCreateTime = dbInstance.getInstanceCreateTime();
    		    	if (!isNewRDSInstance(rdsInstanceCreateTime, new Date(), logger)){
    		    		//this is an old instance
    		    		logger.log("An existing RDS Instance " + dbInstance.getDBInstanceIdentifier() + " is being backed up");
    		    		return "An existing RDS Instance " + dbInstance.getDBInstanceIdentifier() + " is being backed up";
    		    	}
    		    	
    		    	
    		    }
    		    
    		    
    		    List<com.amazonaws.services.rds.model.Tag> tagList = dbInstance.getTagList();
    		    
    		    StringBuffer databaseMetadataStringBuffer = new StringBuffer();
    		    databaseMetadataStringBuffer.append("");
    		    databaseMetadataStringBuffer.append("sys_class_name=").append(systemClassMap.get(dbInstance.getEngine()));
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("u_cloud_provider=").append("AWS (Amazon)");
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("support_group=").append("Cloud Database Support");
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("ip_address=").append("N/A");
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("u_account_id=").append(accountId);
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("u_dbms_version=").append(dbInstance.getEngineVersion());
    		    databaseMetadataStringBuffer.append("\n");
    		    
    		    DBCluster dbCluster = null;
    		    //for Aurora [Postgres, MySQL, DocumentDB, Neptune] cluster info is available
    		    if (engine.equalsIgnoreCase("aurora-mysql") || engine.equalsIgnoreCase("aurora-postgresql")
    		    		|| engine.equalsIgnoreCase("docdb") || engine.equalsIgnoreCase("neptune")){
    		    	
    		    	String clusterIdentifier = dbInstance.getDBClusterIdentifier();
    		    	databaseIdentifier = clusterIdentifier;
    		    	
    		    	DescribeDBClustersRequest dbClusterRequest = new DescribeDBClustersRequest();
    			    dbClusterRequest.setDBClusterIdentifier(clusterIdentifier);
    			    DescribeDBClustersResult dbClustersResult = rdsClient.describeDBClusters(dbClusterRequest);
    			    dbCluster = dbClustersResult.getDBClusters().get(0);
    			    
    			    if (dbCluster == null){
    			    	logger.log(engine + " DB Cluster is null!!");
    			    	return engine + " clusterIdentifier + " + " is not found"; 
    			    }
    			    
    			    databaseMetadataStringBuffer.append("u_host_name=").append(dbCluster.getEndpoint());
    			    databaseMetadataStringBuffer.append("\n");
    			    databaseMetadataStringBuffer.append("tcp_port=").append(dbCluster.getPort());
    			    databaseMetadataStringBuffer.append("\n");
    			    databaseMetadataStringBuffer.append("u_encrypted=").append(dbCluster.isStorageEncrypted());
    			    databaseMetadataStringBuffer.append("\n");
    			    
    		    } else {
    		    	
    		    	databaseIdentifier = dbInstance.getDBInstanceIdentifier();
    		    	
    		    	Endpoint endPoint = dbInstance.getEndpoint();
    		    	String address = null;
    		    	String port = null;
    		    	
    		    	if (endPoint != null){
    		    		address = endPoint.getAddress();
    		    		port = endPoint.getPort().toString();
    		    	}
    		    	databaseMetadataStringBuffer.append("u_host_name=").append(address);
    			    databaseMetadataStringBuffer.append("\n");
    			    databaseMetadataStringBuffer.append("tcp_port=").append(port);
    			    databaseMetadataStringBuffer.append("\n");
    			    String connectionString = null;
    			    
    			    if (engine.startsWith("oracle") && address != null && port != null){
    			    	connectionString = dbInstance.getDBName() + "=(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=" +
    			                     address + ")(PORT=" + port + ")))(CONNECT_DATA=(SERVICE_NAME=" + dbInstance.getDBName() + ")))";
    			    }
    			    
    			    databaseMetadataStringBuffer.append("u_connection_string=").append(connectionString);
    			    databaseMetadataStringBuffer.append("\n");
    			    databaseMetadataStringBuffer.append("u_encrypted=").append(dbInstance.isStorageEncrypted());
    			    databaseMetadataStringBuffer.append("\n");
    		    	
    		    }
    		    			    			    
    		    
    		    databaseMetadataStringBuffer.append("u_instance_name=").append(dbInstance.getDBInstanceIdentifier());
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("dns_domain=").append("rds.amazonaws.com");
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("u_instance_type=").append("DBMS Instance");
    		    databaseMetadataStringBuffer.append("\n");
    		    
    		    
    		    databaseMetadataStringBuffer.append("u_database_cluster_identifier=").append(dbInstance.getDBClusterIdentifier());
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("u_database_name=").append(dbInstance.getDBName());
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("u_support_model=").append("Outsourced");
    		    databaseMetadataStringBuffer.append("\n");
    		    
    		    logger.log("TagList=" + tagList.toString());
    		    int tagArrayLength = tagList.size();
    		    boolean flag1 = false,flag2=false,flag3=false,flag4=false,flag5=false,flag6 = false, flag7 = false;
    		    
    		    for (int i=0; i< tagArrayLength;i++){
    		    	com.amazonaws.services.rds.model.Tag rdsTag = tagList.get(i);
    		    	
    		    	if (rdsTag.getKey().equalsIgnoreCase("barometer-it")){
    		    		databaseMetadataStringBuffer.append("u_supported_applications=").append(rdsTag.getValue()).append("\n");
    		    		flag1 = true;
    		    	}
    		    	if (rdsTag.getKey().equalsIgnoreCase("privacy-data")){
    		    		databaseMetadataStringBuffer.append("u_dcc_pr=").append(rdsTag.getValue()).append("\n");
    		    		flag2 = true;
    		    	}
    		    	if (rdsTag.getKey().equalsIgnoreCase("financial-regulatory-data")){
    		    		databaseMetadataStringBuffer.append("u_dcc_fr=").append(rdsTag.getValue()).append("\n");
    		    		flag3 = true;
    		    	}
    		    	if (rdsTag.getKey().equalsIgnoreCase("legal-data")){
    		    		databaseMetadataStringBuffer.append("u_dcc_la=").append(rdsTag.getValue()).append("\n");
    		    		flag4 = true;
    		    	}
    		    	if (rdsTag.getKey().equalsIgnoreCase("financial-internal-data")){
    		    		databaseMetadataStringBuffer.append("u_dcc_fi=").append(rdsTag.getValue()).append("\n");
    		    		flag5 = true;
    		    	}
    		    	if (rdsTag.getKey().equalsIgnoreCase("environment")){
    		    		databaseMetadataStringBuffer.append("u_environment=").append(rdsTag.getValue()).append("\n");
    		    		flag6 = true;
    		    	}
    		    	if (rdsTag.getKey().equalsIgnoreCase("company")){
    		    		String companyName = rdsTag.getValue();
    		    		if (companyName.equalsIgnoreCase("antm")){
    		    			companyName = "Anthem";
    		    		}
    		    		databaseMetadataStringBuffer.append("u_originating_company=").append(companyName).append("\n");
    		    		flag7 = true;
    		    	}
    		    	
    		    	if (flag1 && flag2 && flag3 && flag4 && flag5 && flag6 && flag7){
    		    		break;
    		    	}
    		    	
    		    }
    		    
    		    logger.log("Flags status : " + (flag1 && flag2 && flag3 && flag4 && flag5 && flag6));
    		  
    		    databaseMetadataStringBuffer.append("u_dcc_bu=").append("Inherit from Application");
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("u_bcc_rt=").append("Inherit from Application");
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("u_bcc_ac=").append("Inherit from Application");
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("u_network_access_type=").append("Open");
    		    databaseMetadataStringBuffer.append("\n");
    		    databaseMetadataStringBuffer.append("u_authentication_method=").append("DBMS");
    		    databaseMetadataStringBuffer.append("\n");
    		    
    		    logger.log("$$$$$$$$$$$$$$$$$$$$$$$$$$$ " + engine + " Start $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
    		    logger.log(databaseMetadataStringBuffer.toString());
    		    logger.log("$$$$$$$$$$$$$$$$$$$$$$$$$$$ " + engine  + " End $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
    		    
    		    
    		    
    		    logger.log("Prepare message ");
			    
			    StringBuffer message = new StringBuffer();
			    message.append("The following Database has just been created");
			    message.append("\n");
			    message.append("\n");
			    message.append("ARN: " + dbInstance.getDBInstanceArn());
			    message.append("\n");
			    message.append("\n");
			    message.append("===================Properties===========================");
			    message.append("\n");
			    message.append(databaseMetadataStringBuffer.toString());
			    message.append("\r\n");
			    message.append("\r\n");
			    message.append("PS. This message is being sent from the function: " + context.getFunctionName() + " to the topic: " + snsTopic +  "\n");
			    
			    logger.log(engine + ": Sending notification... ");
			    boolean isNotificationSent = sendCreateDBSNSNotification(message.toString(), logger, region, accountId, databaseIdentifier);
			    if (isNotificationSent == true){
			    	logger.log(engine + ": Success! Sent message to SNS Topic: " + snsTopic);
			    }else {
			    	logger.log(engine + ": Fail! Failed to send message to SNS Topic: " + snsTopic);
			    }
			    
			    //Now write to a file
			    File inventoryFile = new File("/tmp/wdb-inventory_" + dbInstance.getDBInstanceIdentifier() + ".properties");
			    boolean isFileWriteSuccessful = writeToFile(inventoryFile, databaseMetadataStringBuffer, logger);
			    if (!isFileWriteSuccessful){
			    	logger.log(engine + ": Unable to write to file /tmp/wdb-inventory.properties");
			    	return engine + ": Unable to write to file /tmp/wdb-inventory.properties";
			    }
			    
			    String keyName = "Anthem-Cloud-Databases/" + dateString + "/" + accountId + "_" + region + "_" + engine + "_" + dbiResourceId + "_" + dbInstance.getDBInstanceIdentifier() + "_created.properties";
			    
			    boolean isS3WriteSuccessful = pushToHubS3Bucket(inventoryFile, keyName, logger);
			    if (!isS3WriteSuccessful){
			    	logger.log(engine + ": Unable to insert into S3 bucket " + bucketName);
			    	return engine + ": Unable to insert into S3 bucket " + bucketName;
			    }
			    
			    
            	
            	
            } else if (source.equalsIgnoreCase("aws.redshift")){
            	
            	//DynamoDB -- needs a client of its own
		    	logger.log("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@This is a Redshift event@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@");
		    	
		    	JsonElement eventNameJsonElement = (eventJsonObject.getAsJsonObject("detail")).get("eventName");
			    if (eventNameJsonElement == null){
			    	logger.log("eventName is null/not present: Exiting ");
			    	return "Eventname is empty; Not a Redshift Event";
			    }
		    	
		    	String eventName = eventNameJsonElement.getAsString();
			    
		    	if ( !(eventName.equalsIgnoreCase("CreateCluster"))  ){
			    	logger.log("Not a Redshift CreateTable  Event");
			    	return "Not a Redshift CreateCluster Event";
			    }
		    	
		    	JsonElement requestParametersClusterElement = eventJsonObject.getAsJsonObject("detail").getAsJsonObject("requestParameters").get("clusterIdentifier");
			    String clusterName = requestParametersClusterElement.getAsString();
			    
			   
			    
		    	
		    	final AmazonRedshift redshiftClient = AmazonRedshiftClientBuilder.defaultClient();
		    	DescribeClustersRequest describeClustersRequest = new DescribeClustersRequest();
		    	describeClustersRequest.setClusterIdentifier(clusterName);
		    	
		    	DescribeClustersResult describeClustersResult = redshiftClient.describeClusters(describeClustersRequest);
		    	Cluster redshiftCluster = describeClustersResult.getClusters().get(0);
		    	
		    	String engine = "redshift";
		    	
		    	
			    List<com.amazonaws.services.redshift.model.Tag> tagList =  redshiftCluster.getTags();
			    StringBuffer redshiftProperties = new StringBuffer();
			    
			    
			    com.amazonaws.services.redshift.model.Endpoint  endPoint = redshiftCluster.getEndpoint();
		    	String address = null;
		    	String port = null;
		    	
		    	if (endPoint != null){
		    		address = endPoint.getAddress();
		    		port = endPoint.getPort().toString();
		    	}
		    	redshiftProperties.append("u_host_name=").append(address);
		    	redshiftProperties.append("\n");
		    	redshiftProperties.append("tcp_port=").append(port);
		    	redshiftProperties.append("\n");
			    
			    
			    redshiftProperties.append("");
			    redshiftProperties.append("sys_class_name=").append(systemClassMap.get("redshift"));
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_cloud_provider=").append("AWS(Amazon)");
			    redshiftProperties.append("\n");
			    redshiftProperties.append("support_group=").append("Cloud Database Support");
			    redshiftProperties.append("\n");
			    redshiftProperties.append("ip_address=").append("N/A");
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_account_id=").append(accountId);
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_dbms_version=").append("N/A");
			    redshiftProperties.append("\n");		    
			    redshiftProperties.append("u_instance_name=").append(redshiftCluster.getDBName());
			    redshiftProperties.append("\n");
			    redshiftProperties.append("dns_domain=").append("redshift.amazonaws.com");
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_instance_type=").append("DBMS Instance");
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_connection_string=").append("");
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_encrypted=").append(redshiftCluster.isEncrypted());
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_database_cluster_identifier=").append(clusterName);
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_database_name=").append(redshiftCluster.getDBName());
			    redshiftProperties.append("\n");
			    
			    
			    
			    redshiftProperties.append("u_originating_company=").append("Anthem");
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_support_model=").append("Outsourced");
			    redshiftProperties.append("\n");
			    
			    int tagArrayLength = tagList.size();
			    boolean flag1 = false,flag2=false,flag3=false,flag4=false,flag5=false,flag6 = false, flag7 = false;
			    
			    		    
			    for (int i=0; i< tagArrayLength;i++){
			    	com.amazonaws.services.redshift.model.Tag rdsTag = tagList.get(i);
			    	
			    	if (rdsTag.getKey().equalsIgnoreCase("barometer-it")){
			    		redshiftProperties.append("u_supported_applications=").append(rdsTag.getValue()).append("\n");
			    		flag1 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("privacy-data")){
			    		redshiftProperties.append("u_dcc_pr=").append(rdsTag.getValue()).append("\n");
			    		flag2 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("financial-regulatory-data")){
			    		redshiftProperties.append("u_dcc_fr=").append(rdsTag.getValue()).append("\n");
			    		flag3 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("legal-data")){
			    		redshiftProperties.append("u_dcc_la=").append(rdsTag.getValue()).append("\n");
			    		flag4 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("financial-internal-data")){
			    		redshiftProperties.append("u_dcc_fi=").append(rdsTag.getValue()).append("\n");
			    		flag5 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("environment")){
			    		redshiftProperties.append("u_environment=").append(rdsTag.getValue()).append("\n");
			    		flag6 = true;
			    	}
			    	if (rdsTag.getKey().equalsIgnoreCase("company")){
			    		String companyName = rdsTag.getValue();
			    		if (companyName.equalsIgnoreCase("antm")){
			    			companyName = "Anthem";
			    		}
			    		redshiftProperties.append("u_environment=").append(companyName).append("\n");
			    		flag7 = true;
			    	}
			    	if (flag1 && flag2 && flag3 && flag4 && flag5 && flag6 && flag7){
			    		break;
			    	}
			    	
			    }
			    
			    logger.log("Flags status : " + (flag1 && flag2 && flag3 && flag4 && flag5 && flag6 && flag7));
			  
			    redshiftProperties.append("u_dcc_bu=").append("Inherit from Application");
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_bcc_rt=").append("Inherit from Application");
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_bcc_ac=").append("Inherit from Application");
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_network_access_type=").append("Open");
			    redshiftProperties.append("\n");
			    redshiftProperties.append("u_authentication_method=").append("DBMS");
			    redshiftProperties.append("\n");
			    
			    
			    logger.log("$$$$$$$$$$$$$$$$$$$$$$$$$$$ Redshift Properties Start $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
			    logger.log(redshiftProperties.toString());
			    logger.log("$$$$$$$$$$$$$$$$$$$$$$$$$$$ Redshift Properties End $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
			    
			    
			    
                logger.log("Prepare message ");
			    
			    StringBuffer message = new StringBuffer();
			    message.append("The following Database has just been created");
			    message.append("\n");
			    message.append("\n");
			    message.append("ARN: " + redshiftCluster.getClusterNamespaceArn());
			    message.append("\n");
			    message.append("\n");
			    message.append("===================Properties===========================");
			    message.append("\n");
			    message.append(redshiftProperties.toString());
			    message.append("\r\n");
			    message.append("\r\n");
			    message.append("PS. This message is being sent from the function: " + context.getFunctionName() + " to the topic: " + snsTopic +  "\n");
			    
			    logger.log(engine + ": Sending notification... ");
			    boolean isNotificationSent = sendCreateDBSNSNotification(message.toString(), logger, region, accountId, clusterName);
			    if (isNotificationSent == true){
			    	logger.log(engine + ": Success! Sent message to SNS Topic: " + snsTopic);
			    }else {
			    	logger.log(engine + ": Fail! Failed to send message to SNS Topic: " + snsTopic);
			    }
			    
			    //Now write to a file
			    File inventoryFile = new File("/tmp/wdb-inventory_" + redshiftCluster.getClusterIdentifier() + ".properties");
			    boolean isFileWriteSuccessful = writeToFile(inventoryFile, redshiftProperties, logger);
			    if (!isFileWriteSuccessful){
			    	logger.log(engine + ": Unable to write to file /tmp/wdb-inventory.properties");
			    	return engine + ": Unable to write to file /tmp/wdb-inventory.properties";
			    }
			    
			    String keyName = "Anthem-Cloud-Databases/" + dateString + "/" + accountId + "_" + region + "_" + engine +  "_" + redshiftCluster.getClusterIdentifier() + "_created.properties";
			    
			    boolean isS3WriteSuccessful = pushToHubS3Bucket(inventoryFile, keyName, logger);
			    if (!isS3WriteSuccessful){
			    	logger.log(engine + ": Unable to insert into S3 bucket " + bucketName);
			    	return engine + ": Unable to insert into S3 bucket " + bucketName;
			    }
			    
			    
            	
            }
            
            else {
		    	logger.log("This is not an RDS or DynamoDB or Redshift event");
		    	return "This is not an RDS or DynamoDB or Redshift event";
		    }
		    
		    
		   
		    
		  //******************************************* RDS Code ends ********************************************************* 
		    
	    	
	    	
		    return "Success!";
	   }
	   
	   private boolean sendCreateDBSNSNotification(String message, LambdaLogger logger, String... configurationValues ){
		   
		    String serviceEndpoint = "https://sts." + region + ".amazonaws.com";
		    AwsClientBuilder.EndpointConfiguration endPointConfig = 
					   new AwsClientBuilder.EndpointConfiguration(serviceEndpoint, region);
		       String assumedRoleName = "sns-target-assumed-role";
			   
			   AWSSecurityTokenService stsClient = AWSSecurityTokenServiceClientBuilder.standard().withEndpointConfiguration(endPointConfig)
						                           .build();

				AssumeRoleRequest roleRequest = new AssumeRoleRequest().withRoleArn(targetRoleArn)
						.withRoleSessionName(assumedRoleName);
				AssumeRoleResult assumeRoleResult = null;

				
				assumeRoleResult = stsClient.assumeRole(roleRequest);
				

				Credentials sessionCredentials = assumeRoleResult.getCredentials();

				BasicSessionCredentials basicSessionCredentials = new BasicSessionCredentials(
						sessionCredentials.getAccessKeyId(), sessionCredentials.getSecretAccessKey(),
						sessionCredentials.getSessionToken());

		    AWSStaticCredentialsProvider credentialsProvider = new AWSStaticCredentialsProvider(basicSessionCredentials);
		    
		    
		    final AmazonSNS snsClient = AmazonSNSClientBuilder.standard().withCredentials(credentialsProvider).build();
		    logger.log("Sending message to SNS Topic: " + snsTopic);
		    
		    boolean configValuesPresent = false;
		    if (configurationValues != null && configurationValues.length == 3){
		    	configValuesPresent = true;
		    }
		    
		    PublishResult snsPublishResult;
		    
		    if (configValuesPresent == true){
		    	snsPublishResult = snsClient.publish(snsTopic, message.toString(),"EH Cloud Database Services Create Notification for " + configurationValues[0] + ":" + configurationValues[1] + ":" + configurationValues[2] );
		    } else {
		    	snsPublishResult = snsClient.publish(snsTopic, message.toString(),"EH Cloud Database Services Create Notification" );
		    }
		    
		    
		    
		    logger.log("SNS Publish status : " + snsPublishResult.getMessageId());
		    if (snsPublishResult.getMessageId() != null){
		    	return true;
		    }
		    
		    return false;
		    		   
	   }
    
    
	   private boolean writeToFile(File inventoryFile ,StringBuffer propertiesStringBuffer, LambdaLogger logger){
		     
		    try{
		      PrintWriter out = new PrintWriter(inventoryFile);
		      out.println(propertiesStringBuffer.toString());
		      out.flush();
		      out.close();
		     
		    }catch(FileNotFoundException fnfe){
		    	logger.log("File wdb-inventory.txt file not found " + fnfe.getMessage());
		    	return false;
		    }
		    return true;
		   
	   }
	   
	   private boolean pushToHubS3Bucket(File inventoryFile, String keyName,  LambdaLogger logger){
		   
		   logger.log("^^^^^^^^^^^^^^^^^^^^Inside pushToHubS3Bucket ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^");
		   logger.log("Keyname: " + keyName);
		   logger.log("File: " + inventoryFile.getTotalSpace());
		   
		   
		   String serviceEndpoint = "https://sts." + region + ".amazonaws.com";
		   logger.log("Service Endpoint Region: " + serviceEndpoint);
		   AwsClientBuilder.EndpointConfiguration endPointConfig = 
				   new AwsClientBuilder.EndpointConfiguration(serviceEndpoint, region);
	       String assumedRoleName = "target-assumed-role";
		   
		   AWSSecurityTokenService stsClient = AWSSecurityTokenServiceClientBuilder.standard().withEndpointConfiguration(endPointConfig)
					                           .build();

			AssumeRoleRequest roleRequest = new AssumeRoleRequest().withRoleArn(targetRoleArn)
					.withRoleSessionName(assumedRoleName);
			AssumeRoleResult assumeRoleResult = null;

			try{
			   assumeRoleResult = stsClient.assumeRole(roleRequest);
			} catch(Exception e){
				logger.log("Exception while assuming role: " + e.getMessage());
				String message = "Error when assuming role " + targetRoleArn + ", " + e.getMessage();
				sendCreateDBSNSNotification(message, logger);
				return false;
				
			}

			Credentials sessionCredentials = assumeRoleResult.getCredentials();

			BasicSessionCredentials basicSessionCredentials = new BasicSessionCredentials(
					sessionCredentials.getAccessKeyId(), sessionCredentials.getSecretAccessKey(),
					sessionCredentials.getSessionToken());

			AWSStaticCredentialsProvider credentialsProvider = new AWSStaticCredentialsProvider(basicSessionCredentials);
		   
		 
		   //AmazonS3 s3 = AmazonS3ClientBuilder.standard().withEndpointConfiguration(new EndpointConfiguration(vpcEndpoint,region
	   	   //			   )).withCredentials(credentialsProvider).build();
		   
			AmazonS3 s3 = AmazonS3ClientBuilder.standard().withCredentials(credentialsProvider).withRegion(region).build();
		   
		  
		    
		    
	    	try{
	    		
	    	   logger.log("Before inserting the file to the s3 bucket:  " + bucketName + " with Keyname: " + keyName);
	    	   PutObjectResult objectResult = s3.putObject(bucketName, keyName, inventoryFile);
	    	   logger.log("Printing version id: " + objectResult.getVersionId());
	    	}
	    	catch(AmazonServiceException ase){
	    	   logger.log("Exception while writing S3 data (Message): " + ase.getMessage());
	    	   logger.log("Exception while writing S3 data (Status): " + ase.getStatusCode());
	    	   sendCreateDBSNSNotification("Exception while writing S3 data (Message): " + keyName + ", Error Message:  " +  ase.getMessage(), logger);
	    	   //ase.printStackTrace();
	    	   return false;
	    	}
	    	
	    	
	    	return true;
		   
	   }
	   
	   private boolean isNewRDSInstance(Date creationTime, Date currentTime, LambdaLogger logger){
		   
		   Calendar calCreationInstance = Calendar.getInstance();
		   Calendar calBackupInstance = Calendar.getInstance();
		   
		   calCreationInstance.setTime(creationTime);
		   calBackupInstance.setTime(currentTime);
		   
		   long creationTimeInMillis = calCreationInstance.getTimeInMillis();
		   long backupTimeInMillis = calBackupInstance.getTimeInMillis();
		   
		   logger.log("creationTimeInMillis: " + creationTimeInMillis );
		   logger.log("backupTimeInMillis: " + backupTimeInMillis );
		   
		   int creationTimeInHours = (int)(creationTimeInMillis / ( 1000 * 60 * 60 )); 
		   int backupTimeInHours = (int)(backupTimeInMillis / ( 1000 * 60 * 60 )); 
		   
		   logger.log("creationTimeInHours: " + creationTimeInHours );
		   logger.log("backupTimeInHours: " + backupTimeInHours );
		   
		   if ((backupTimeInHours - creationTimeInHours) > 2){
			   return false;
		   }
		   
		   return true;
		   
	   }
    
}

