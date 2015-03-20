CURRENT_DIR=`pwd`;
cd zookeeper
java -cp zookeeper-3.4.6.jar:lib/slf4j-api-1.6.1.jar:lib/slf4j-log4j12-1.6.1.jar:lib/log4j-1.2.16.jar:conf org.apache.zookeeper.server.quorum.QuorumPeerMain custom.cfg;
cd $CURRENT_DIR;
