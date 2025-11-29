# Init Authentication
curl -s -X POST http://172.17.0.2:8091/clusterInit \
  -d "username=ycsb_admin" \
  -d "password=ycsb_passwd" \
  -d "services=kv,n1ql,index" \
  -d "memoryQuota=512" \
  -d "indexMemoryQuota=256" \
  -d "port=SAME"

# Create Bucket
curl -s -u ycsb_admin:ycsb_passwd -X POST \
  "http://172.17.0.2:8091/pools/default/buckets" \
  -d name=ycsb -d bucketType=couchbase -d ramQuota=256
