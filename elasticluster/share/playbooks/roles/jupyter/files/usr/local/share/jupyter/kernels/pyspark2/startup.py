# THIS FILE IS CONTROLLED BY ELASTICLUSTER
# local modifications will be overwritten
# the next time `elasticluster setup` is run!
#

# Configure the necessary Spark environment
#
# Originally from: http://ramhiser.com/2015/02/01/configuring-ipython-notebook-support-for-pyspark/
#
import os
import sys

join = os.path.join

if 'SPARK_HOME' not in os.environ:
    os.environ['SPARK_HOME'] = '/usr/lib/spark'
spark_home = os.environ['SPARK_HOME']

# by default Spark uses the "local" executor, use YARN instead
os.environ.setdefault('MASTER', 'yarn-client')
os.environ.setdefault('SPARK_JAR', '/usr/lib/spark/lib/spark-assembly.jar')
os.environ.setdefault('SPARK_YARN_APP_JAR', '/dev/null')

# make `pyspark` and `py4j` available to this process
spark_home_python = join(spark_home, "python")

# make `pyspark` and `py4j` available on PYTHONPATH so it's read by children processes
spark_pythonpath = ('{spark_home_python}:{spark_home_python}/pyspark:{spark_home_python}/lib/py4j-src.zip'.format(**locals()))
if 'PYTHONPATH' in os.environ:
    os.environ['PYTHONPATH'] += ':' + spark_pythonpath
else:
    os.environ['PYTHONPATH'] = spark_pythonpath

# Initialize PySpark to predefine the SparkContext variable 'sc'
execfile(join(spark_home_python, 'pyspark/shell.py'))
