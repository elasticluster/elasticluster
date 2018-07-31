import os

from flask import Flask, json, Response
from flask_restplus import Api, Resource

from elasticluster import log
from elasticluster.conf import make_creator
from elasticluster.exceptions import ClusterNotFound, ConfigurationError

app = Flask('elasticluster api server')
api = Api(app, appversion='1.0', title='ElastiCluster API', description='Manage clusters with ElastiCluster')


def default_settings():
    return os.path.expanduser("~/.elasticluster/config"), os.path.expanduser("~/.elasticluster/storage")


@api.route('/clusters')
class Clusters(Resource):
    def get(self):
        """ list all active clusters """
        config, storage = default_settings()
        creator = make_creator(config, storage)
        repository = creator.create_repository()
        stat = []
        for c in repository.get_all():
            stat.append(c.to_dict(omit=('_cloud_provider',
                                        '_naming_policy',
                                        '_setup_provider',
                                        'repository',
                                        'storage_file',
                                        'nodes'
                                        )))
        return Response(json.dumps(stat),  mimetype="application/json")


@api.route('/templates')
class Templates(Resource):
    def get(self):
        """ list all available templates """
        config, storage = default_settings()
        creator = make_creator(config, storage)
        config = creator.cluster_conf
        return Response(json.dumps(config.keys()), mimetype="application/json")


@api.route('/nodes/<string:name>', endpoint='/nodes')
@api.doc(params={'name': 'Name of the cluster'})
class Nodes(Resource):
    @api.doc(responses={
             200: 'Success',
             404: 'Cluster not found'
    })
    def get(self, name):
        """ get all nodes for a cluster with a specific name """
        config, storage = default_settings()
        creator = make_creator(config, storage)
        try:
            cluster = creator.load_cluster(name)
        except (ClusterNotFound, ConfigurationError) as ex:
            log.error("api error: Listing nodes from cluster {0}: {1}".format(name, ex))
            api.abort(404, 'Cluster not found')

        stat = []
        for cls in cluster.nodes:
            for node in cluster.nodes[cls]:
                np = {}
                for line in node.pprint().splitlines():
                    if ':' not in line:
                        np['name'] = line
                    else:
                        np[line.split(':')[0].strip()] = line.split(':')[1].strip()
                stat.append(np)
        return Response(json.dumps(stat), mimetype="application/json")


@api.route('/start')
class Start(Resource):
    start_parser = api.parser()
    start_parser.add_argument('key', help='Name of the key pair', location='form', required=True)
    start_parser.add_argument('template', help='Name of the template you want to launch', location='form', required=True)
    start_parser.add_argument('name', help='New name for the cluster', location='form', required=True)

    @api.doc(responses={
                 200: 'Success',
                 406: 'Template with that name does not exist',
                 409: 'Cluster with that name already exists',
                 417: 'Setup incomplete, cluster may be in an inconsistent state',
                 418: 'Initialization failed, configuration error',
    })
    @api.expect(start_parser)
    def post(self):
        """ Start a new cluster based on a specific template """
        args = self.start_parser.parse_args()
        config, storage = default_settings()
        creator = make_creator(config, storage)
        repository = creator.create_repository()
        cluster = next(iter([c for c in repository.get_all() if c.name == args.name]), None)
        if not cluster:
            template = next(iter([k for k in creator.cluster_conf.keys() if k == args.template]), None)
            if template:
                try:
                    cluster = creator.create_cluster(args.template, args.name, user_key_name=args.key)
                except ConfigurationError as ex:
                    log.error("api error; Starting cluster {0}: {1}".format(args.template, ex))
                    api.abort(418, 'Initialization failed, configuration error')
            else:
                api.abort(406, 'Template with that name does not exist')
        else:
            api.abort(409, 'Cluster with that name already exists')

        cluster.start()
        log.info("Configuring cluster `{0}`...".format(args.name))
        if not cluster.setup():
            api.abort(417, 'Setup incomplete, cluster may be in an inconsistent state')


@api.route('/stop/<string:name>', endpoint='/stop')
@api.doc(params={'name': 'Name of the cluster'})
class Stop(Resource):
    @api.doc(responses={
                 200: 'Success',
                 404: 'Cluster not found'
             })
    def post(self, name):
        """ Stop a cluster with a specific name """
        config, storage = default_settings()
        creator = make_creator(config, storage)
        try:
            cluster = creator.load_cluster(name)
        except (ClusterNotFound, ConfigurationError) as ex:
            log.error("api error: Cannot stop cluster `{0}`: {1}".format(name, ex))
            api.abort(404, 'Cluster not found')

        log.warn("Destroying cluster `{0}` ...".format(name))
        cluster.stop()


@api.route('/setup/<string:name>')
@api.doc(params={'name': 'Name of the cluster'})
class Setup(Resource):
    @api.doc(responses={
                 200: 'Success',
                 404: 'Cluster not found',
                 417: 'Setup incomplete, cluster may be in an inconsistent state'
             })
    def post(self, name):
        """ Redo a cluster setup """
        config, storage = default_settings()
        creator = make_creator(config, storage)
        try:
            cluster = creator.load_cluster(name)
            cluster.update()
        except (ClusterNotFound, ConfigurationError) as ex:
            log.error("api error: Setting up cluster {0}: {1}".format(name, ex))
            api.abort(404, 'Cluster not found')

        log.info("Configuring cluster `{0}`...".format(name))
        if not cluster.setup():
            api.abort(417, 'Setup incomplete, cluster may be in an inconsistent state')


@api.route('/resize')
class Resize(Resource):
    resize_parser = api.parser()
    resize_parser.add_argument('name', help='Cluster to resize', location='form', required=True)
    resize_parser.add_argument('action', choices=('add', 'remove'), help='Add or remove nodes', location='form', required=True)
    resize_parser.add_argument('group', help='Name of the group (master, worker, etc.)', location='form', required=True)
    resize_parser.add_argument('number', type=int, help='Number of nodes to add/remove', location='form', required=True)

    @api.doc(responses={
                 200: 'Success',
                 404: 'Cluster not found',
                 406: 'Could not find defined group in existing cluster',
                 417: 'Setup incomplete, cluster may be in an inconsistent state'
             })
    @api.expect(resize_parser)
    def post(self):
        """ Resize an existing cluster """
        args = self.resize_parser.parse_args()
        config, storage = default_settings()
        creator = make_creator(config, storage)
        try:
            cluster = creator.load_cluster(args.name)
            cluster.update()
        except (ClusterNotFound, ConfigurationError) as ex:
            log.error('api error: {0}'.format(ex))
            api.abort(404, 'Cluster not found')

        if args.group not in cluster.nodes or not cluster.nodes[args.group]:
            log.error("api error: Elasticluster can not infer which template to use for the new node(s).")
            api.abort(406, 'Could not find defined group in existing cluster')

        if args.action == 'add':
            log.info('trying to add {0} nodes of type {1} to {2}'.format(args.number,
                                                                         args.group,
                                                                         args.name))
            sample_node = cluster.nodes[args.group][0]
            for i in range(args.number):
                cluster.add_node(args.group,
                                 sample_node.image_id,
                                 sample_node.image_user,
                                 sample_node.flavor,
                                 sample_node.security_group,
                                 image_userdata=sample_node.image_userdata,
                                 **sample_node.extra)
        else:
            log.info('trying to remove {0} nodes of type {1} to {2}'.format(args.number,
                                                                            args.group,
                                                                            args.name))
            to_remove = cluster.nodes[args.group][-args.number:]
            log.warn("The following nodes will be removed from the cluster: {0}"
                     .format(str.join("\n    ", [n.name for n in to_remove])))
            for node in to_remove:
                cluster.nodes[args.group].remove(node)
                node.stop()

        cluster.start()
        if not cluster.setup():
            api.abort(417, 'Setup incomplete, cluster may be in an inconsistent state')
