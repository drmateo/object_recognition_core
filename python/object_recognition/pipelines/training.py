'''
Loaders for all object recognition pipelines
'''
from abc import ABCMeta, abstractmethod
import inspect
from pydoc import ispackage
from inspect import ismodule
import pkgutil

import ecto
from ecto_object_recognition import capture
from object_recognition.common.utils import list_to_cpp_json_str
from object_recognition.common.utils.json_helper import dict_to_cpp_json_str

class ObservationDealer(ecto.BlackBox):
    '''
    At each iteration, will return one fully typed observation, K,R,T,image,depth,mask, etc...
    Initialized with a predetermined set of observation ids.
    '''
    db_reader = capture.ObservationReader
    def declare_params(self, p):
        p.declare('observation_ids', 'An iterable of observation ids.', [])
        p.declare('db_params', 'db parameters.', '')

    def declare_io(self, p, i, o):
        self.db_reader = capture.ObservationReader(db_params=p.db_params)
        self.observation_dealer = ecto.Dealer(tendril=self.db_reader.inputs.at('observation'),
                                              iterable=p.observation_ids)
        o.forward_all('db_reader')

    def connections(self):
        graph = [self.observation_dealer[:] >> self.db_reader['observation']]
        return graph

class ModelBuilder(ecto.BlackBox):
    def __init__(self, source, incremental_model_builder, **kwargs):
        self.source = source
        self.incremental_model_builder = incremental_model_builder
        ecto.BlackBox.__init__(self, **kwargs)

    def declare_params(self, p):
        pass

    def declare_io(self, p, i, o):
        o.forward_all('incremental_model_builder')

    def connections(self):
        graph = []
        # Connect the model builder to the source
        for key in self.source.outputs.iterkeys():
            if key in  self.incremental_model_builder.inputs.keys():
                graph += [self.source[key] >> self.incremental_model_builder[key]]
        return graph

class TrainingPipeline:
    ''' An abstract base class for creating object training pipelines.
    '''
    __metaclass__ = ABCMeta

    @classmethod
    def type_name(cls):
        '''
        Return the code name for your pipeline. eg. 'TOD', 'LINEMOD', 'mesh', etc...
        '''
        raise NotImplementedError("The training pipeline class must return a string name.")

    @abstractmethod
    def incremental_model_builder(self, pipeline_params):
        '''
        Given a dictionary of parameters, return a cell, or BlackBox that takes
        as input observations, and at each iteration and builds up a model
        on its output.
        '''
        raise NotImplementedError("This should return a cell .")


    @abstractmethod
    def post_processor(self, pipeline_params):
        '''
        Given a dictionary of parameters, return a cell, or BlackBox that
        takes the output of the incremental_model_builder and converts it into
        a database document. You may do whatever post processing here.
        '''
        raise NotImplementedError("This should return a cell .")


    @classmethod #see http://docs.python.org/library/abc.html#abc.ABCMeta.__subclasshook__
    def __subclasshook__(cls, C):
        if C is TrainingPipeline:
            #all pipelines must have atleast this function.
            if any("incremental_model_builder" in B.__dict__ for B in C.__mro__):
                return True
        return NotImplemented

    @classmethod
    def train(cls, object_id, session_ids, observation_ids, pipeline_params, db_params):
        '''
        Returns a training plasm, that will be executed exactly once.
        :param object_id: The object id to train up.
        :param session_ids: A list of session ids that this model should be based on.
        :param observation_ids: A list of observation ids that will be dealt to the incremental model builder.
        :param pipeline_params: A dictionary of parameters that will be used to initialize the training pipeline.
        :param db_params: A DB parameters object that specifies where to save the model to.
        '''

        from ecto_object_recognition.object_recognition_db import ModelWriter

        #todo make this depend on the pipeline specification or something...
        dealer = ObservationDealer(db_params=db_params, observation_ids=observation_ids)

        pipeline = cls()
        incremental_model_builder = pipeline.incremental_model_builder(pipeline_params)
        model_builder = ModelBuilder(source=dealer,
                                     incremental_model_builder=incremental_model_builder,
                                     niter=0) #execute until a quit condition occurs.
        post_process = pipeline.post_processor(pipeline_params)

        plasm = ecto.Plasm()
        # Connect the model builder to the source
        for key in model_builder.outputs.iterkeys():
            if key in post_process.inputs.keys():
                plasm.connect(model_builder[key] >> post_process[key])

        writer = ModelWriter(db_params=db_params,
                             object_id=object_id,
                             session_ids=list_to_cpp_json_str(session_ids),
                             model_json_params=dict_to_cpp_json_str(pipeline_params),
                             model_type=cls.type_name()
                             )
        plasm.connect(post_process["db_document"] >> writer["db_document"])
        return plasm



def find_training_pipelines(modules):
    '''
    Given a list of python packages, or modules, find all TrainingPipeline implementations.
    :param modules: A list of python package names, e.g. ['object_recognition']
    :returns: A list of TrainingPipeline implementation classes.
    '''
        pipelines = {}
        ms = []
        for module in modules:
            m = __import__(module)
            ms += [(module, m)]
            for loader, module_name, is_pkg in  pkgutil.walk_packages(m.__path__):
                if is_pkg:
                    module = loader.find_module(module_name).load_module(module_name)
                    ms.append(module)
        for pymodule in ms:
            for x in dir(pymodule):
                potential_pipeline = getattr(pymodule, x)
                if inspect.isclass(potential_pipeline) and potential_pipeline != TrainingPipeline and issubclass(potential_pipeline, TrainingPipeline):
                    pipelines[potential_pipeline.type_name()] = potential_pipeline
        return pipelines