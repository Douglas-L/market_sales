# Market Sales Dash App


This repository is a companion to my [blog post](https://douglas-l.github.io/grass_analytics/journal/Deploying-Dash-App-on-Pythonanywhere.html) on deploying a Dash app on pythonanywhere.com. It contains the three files I used to get my app up and running. 

1. Encoded_df.csv:   
    An anonymized data set spanning roughly a year of market sales
2. Requirements3.6.txt:  
 For setting up your virtual environment
3. Sales_app.py:   
Code for the Dash app. A work in progress, but it currently does three tasks.  
    a. Display the latest individual records with options to filter and change the number of rows displayed    
    b. Display historical sales trends for a single item over the past x days, with options to change the time window  
    c. Estimate the yield by dividing the sales by the number of animals sent to slaughter between those dates. 