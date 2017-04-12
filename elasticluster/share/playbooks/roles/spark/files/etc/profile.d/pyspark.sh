# Additional settings for PySpark

# force PySpark to use the Hadoop/YARN cluster
# (default is to use a local executor) 
export MASTER=yarn-client

# by default, calling `pyspark` starts an IPython interpreter
export PYSPARK_DRIVER_PYTHON=ipython
