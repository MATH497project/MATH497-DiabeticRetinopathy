install.packages("devtools")
library(devtools)
install_github("jackwasey/icd")
library(icd)
# Installation via CRAN does not work for me, 
# I installed munually by the .tar.gz file from 
# https://cran.r-project.org/web/packages/icd/index.html

# Set the working directory
setwd("/Users/Dan/百度云同步盘/丝打底/2017 spring/MATH 497/data")
tb=read.csv('ICD_codes.txt', header=FALSE, as.is=T)

explanation=function(v, flag=FALSE){
  if(flag==TRUE){
    temp=icd_explain(as.icd10(v))
  }
  else{
    temp=icd_explain(as.icd9(v))
  }
  if(length(temp)==0)
    return('Null')
  # For the xx.xx code, which could be icd 9 proceudre code,
  # mark them as 'Null'. Otherwise icd_explain() may regonize them
  # as some short of icd 9 cm codes.
  else if(nchar(unlist(strsplit(v, '[.]'))[1])==2)
    return('Null')
  else
    return(temp)}


# Return all the explanations of all codes. 
# However, ll codes started with E and V will be considered as icd9 codes under testing
# which does not follow my findings.
#ICD_explain=sapply(tb$V1, explanation)
#ICD_tb = data.frame(cbind(tb$V1, ICD_explain), row.names = NULL)
#colnames(ICD_tb) = c('codes', 'official_explanation')
#write.csv(ICD_tb, file = 'ICD_explanation.csv', row.names = FALSE)


separation=function(v){
  # All the v-codes and 'Exxx.xx' codes should belong to icd 9
  # Exclude these codes from icd10_valid
  if(substr(v,1,1)=='V' | (substr(v,1,1)=='E' & nchar(unlist(strsplit(v, '[.]'))[1])==4)){
    return(FALSE);
  }
  else{
    icd_is_valid(as.icd10(v))
  }}

# icd_guess_version also gives all V and E codes with icd9 value
#icd10_valid=sapply(tb$V1, function(v){icd_guess_version(v)=='icd10'})
icd10_valid=sapply(tb$V1, separation)
icd10_codes = tb[icd10_valid,]
icd10_codes = icd_sort(icd10_codes)
icd10_description=sapply(icd10_codes, explanation, flag=TRUE)
icd10_tb=data.frame(cbind(icd10_codes,unlist(icd10_description)), row.names=NULL)
colnames(icd10_tb) =c('codes', 'official_explanation')


icd9_codes=tb[!icd10_valid,]
icd9_codes=icd_sort(icd9_codes)
icd9_description=sapply(icd9_codes, explanation)
icd9_tb=data.frame(cbind(icd9_codes,unlist(icd9_description)), row.names=NULL)
colnames(icd9_tb) =c('codes', 'official_explanation')


write.csv(icd9_tb, file= "icd9_codes_R.csv", row.names=FALSE)
write.csv(icd10_tb, file= "icd10_codes_R.csv", row.names=FALSE)

