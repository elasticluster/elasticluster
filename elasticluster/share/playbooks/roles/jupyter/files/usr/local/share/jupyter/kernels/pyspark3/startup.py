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
os.environ.setdefault('MASTER', 'yarn')
os.environ.setdefault('SPARK_JAR',
                      '{spark_home}/lib/spark-assembly.jar'
                      .format(spark_home=spark_home))
os.environ.setdefault('SPARK_YARN_APP_JAR', '/dev/null')

# make `pyspark` and `py4j` available to this process
spark_home_python = join(spark_home, "python")
sys.path.insert(0, spark_home_python)
sys.path.insert(0, join(spark_home_python, 'pyspark'))
sys.path.insert(0, join(spark_home_python, 'lib/py4j-src.zip'))

# make `pyspark` and `py4j` available on PYTHONPATH so it's read by children processes
spark_pythonpath = ('{spark_home_python}:{spark_home_python}/pyspark'
                    .format(spark_home_python=spark_home_python))
if 'PYTHONPATH' in os.environ:
    os.environ['PYTHONPATH'] += ':' + spark_pythonpath
else:
    os.environ['PYTHONPATH'] = spark_pythonpath

# Initialize PySpark to predefine the SparkContext variable 'sc'
with open(join(spark_home_python, 'pyspark/shell.py')) as spark_shell_py:
    code = compile(spark_shell_py.read(), 'shell.py', 'exec')
    exec(code)

# clean up variables
del spark_home
del spark_home_python
del spark_pythonpath
del spark_shell_py
