install.packages("devtools")
library(devtools)
install_github("jackwasey/icd")
library(icd)
# Installation via CRAN does not work for me, 
# I installed munually by the .tar.gz file from 
# https://cran.r-project.org/web/packages/icd/index.html

# Set the working directory
setwd("/Users/Dan/百度云同步盘/丝打底/2017 spring/MATH 497/data")
tb=read.csv('ICD_codes.csv', header=FALSE, as.is=T)

icd10_valid=sapply(tb$V1, function(v){icd_is_valid(as.icd10(v))})
icd10_codes = tb[icd10_valid,]
icd10_codes = icd_sort(icd10_codes)
icd10_description=sapply(icd10_codes, function(v){
  if(length(icd_explain(v))==0)
    return('Null')
  else
    return(icd_explain(v))})
icd10_tb=data.frame(cbind(icd10_codes,unlist(icd10_description)), row.names=NULL)
colnames(icd10_tb) =c('codes', 'official_explanation')


icd9_codes=tb[!icd10_valid,]
icd9_codes=icd_sort(icd9_codes)
icd9_description=sapply(icd9_codes, function(v){
  if(length(icd_explain(v))==0)
    return('Null')
  else
    return(icd_explain(v))}
  )
icd9_tb=data.frame(cbind(icd9_codes,unlist(icd9_description)), row.names=NULL)
colnames(icd9_tb) =c('codes', 'official_explanation')

# It seems a lot of 
temp=sapply(icd9_codes, function(v){substr(v,1,1)=='E'})
temp1=icd9_tb[temp,]
temp1=temp1[which(temp1[,2]=='Null'),]
icd_explain(as.icd10(temp1$codes))


write.csv(icd9_tb, file= "icd9_codes.csv", row.names=FALSE)
write.csv(icd10_tb, file= "icd10_codes.csv", row.names=FALSE)

