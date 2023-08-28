import json
import os
import boto3
from datetime import datetime
import time

def main(event, context):

    region = os.environ.get('AWS_REGION')

    targetRoleArn = os.environ.get('targetRoleArn')

    rdsClient = boto3.client('rds', region_name=region)
    lambdaClient = boto3.client('lambda', region_name=region)
    logsClient = boto3.client('logs', region_name=region)
    costClient = boto3.client('ce', region_name=region)

    logGroupPrefix = os.environ.get('log_group_prefix')
    startDate = os.environ.get('startDate')

    logGroupServiceMap = {}
    logGroupBillingEntityList = []


    grpDefinition = {}
    grpDefinition['Key']  = "USAGE_TYPE"
    grpDefinition['Type'] = "DIMENSION"

    cloudwatchExpression = {}
    cloudWatchDimensionValues = {}
    cloudWatchDimensionValues["Key"] = "SERVICE"
    cloudWatchDimensionValues["Values"] = ["AmazonCloudWatch"]

    cloudwatchExpression["Dimensions"] = cloudWatchDimensionValues

    usageTypeExpression = {}
    usageTypeDimensionValues = {}
    usageTypeDimensionValues["Key"] = "USAGE_TYPE"
    usageTypeDimensionValues["Values"] = ["USE2-TimedStorage-ByteHrs"]

    usageTypeExpression["Dimensions"] = usageTypeDimensionValues

    expressionList = [cloudwatchExpression, usageTypeExpression]

    cwAndUsageTypeExpression = {
        "And" : expressionList
    }

    isSameYear = True
    today = datetime.now().date()
    monthValue = today.month
    currentYear = today.year

    if startDate is None or startDate.strip().lower() == "":
        print("Start Date has not been set. Hence defaulting to January")
        startDate = "01" + str(currentYear)

    startYear = startDate[2:]
    startYearInt = int(startYear)

    if startYearInt != currentYear:
        isSameYear = False

    if isSameYear == False:

        startMonth = startDate[0:2]

        for i in range(int(startMonth), 13):
            monthEnd = ""
            
            if i in [1, 3, 5, 7, 8, 10, 12]:
                monthEnd = "31"
            elif i in [4, 6, 9, 11]:
                monthEnd = "30"
            else:
                monthEnd = "28"
                
            startDate = f"{startYearInt}-{i:02d}-01"
            endDate = f"{startYearInt}-{i:02d}-{monthEnd}"

            result = costClient.get_cost_and_usage(
                TimePeriod={
                    "Start": startDate,
                    "End": endDate
                },
                Granularity="MONTHLY",
                Metrics=["BlendedCost", "UsageQuantity"],
                Filter=cwAndUsageTypeExpression,
                GroupBy=[grpDefinition]
            )
            print(result)
            
            resultByTimeList = result["ResultsByTime"]
            for resultByTime in resultByTimeList:
                totalList = resultByTime["Groups"][0]["Metrics"]
                bcMetricValue = totalList["BlendedCost"]["Amount"]
                uqMetricValue = totalList["UsageQuantity"]["Amount"]
                logGroupBillingEntity = {
                    "accountNumber": getAccountId(context),
                    "month": getMonthString(i) + " - " + startYear,
                    "amount": bcMetricValue,
                    "sizeInGB": uqMetricValue,
                    "serviceName":"AmazonCloudWatch"
                }

                logGroupBillingEntityList.append(logGroupBillingEntity)
        
        
# end of if (isSameYear == false)

    for i in range(1, monthValue + 1):
        if i == 1 or i == 3 or i == 5 or i == 7 or i == 8 or i == 10 or i == 12:
            monthEnd = "31"
        elif i == 4 or i == 6 or i == 9 or i == 11:
            monthEnd = "30"
        else:
            monthEnd = "28"


        startDate = f"{today.year}-{i:02d}-01"
        endDate = f"{today.year}-{i:02d}-{monthEnd}"


        result = costClient.get_cost_and_usage(
            TimePeriod={
                'Start': startDate,
                'End': endDate
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost', 'UsageQuantity'],
            Filter=cwAndUsageTypeExpression,
            GroupBy=[grpDefinition]
        )

        resultByTimeList = result["ResultsByTime"]
        for resultByTime in resultByTimeList:
            totalList = resultByTime["Groups"][0]["Metrics"]
            bcMetricValue = totalList["BlendedCost"]["Amount"]
            uqMetricValue = totalList["UsageQuantity"]["Amount"]
            
            logGroupBillingEntity = {
                        "accountNumber": getAccountId(context),
                        "month": getMonthString(i) + " - " + str(today.year),
                        "amount": bcMetricValue,
                        "sizeInGB": uqMetricValue,
                        "serviceName":"AmazonCloudWatch"
            }
            
            logGroupBillingEntityList.append(logGroupBillingEntity)
    print(logGroupBillingEntityList)        
    display(logGroupBillingEntityList)
    populateDynamoDBBillingTable("organization-loggroup-test-billing",targetRoleArn, region, logGroupBillingEntityList)

    return "Success!"
