from django.shortcuts import render
#from rest_framework.settings import api_settings
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticatedOrReadOnly,DjangoModelPermissionsOrAnonReadOnly,AllowAny
from rest_framework.views import APIView
#from ccelery.q import QueueTask, list_tasks, task_docstring
#from models import Run_model
from rest_framework.renderers import JSONRenderer, JSONPRenderer
#from renderer import QueueRunBrowsableAPIRenderer
from rest_framework.parsers import JSONParser,MultiPartParser,FormParser,FileUploadParser
#from util import trim
#from rest_framework.authtoken.models import Token
#from django.views.decorators.csrf import csrf_exempt
#from django.utils.decorators import method_decorator
#task = list_tasks()['available_tasks']
#from rest_framework.viewsets import ModelViewSet
#from serializer import FileUploadSerializer
import os,glob,shutil,httplib
from dockertask import docker_task
from subprocess import Popen, PIPE, call
from django.conf import settings
from urlparse import urlparse
import requests

class CheckMapFile(APIView):
    permission_classes = ( AllowAny,)
    renderer_classes = (JSONRenderer,)
    def __init__(self, *args, **kwargs):
        self.docker_cmd = "validate_mapping_file.py -m %s -o %s "
        temp = getattr(settings,"DOCKER_HOST_DATA_DIRECTORY", "/data")
        self.docker_opts = "-v %s:/data" % (temp)
        self.docker_container = "qiime_env"
        super(CheckMapFile, self).__init__(*args, **kwargs)

    def get_username(self, request):
        username = "guest"
        if request.user.is_authenticated():
            username = request.user.username
        return username

    def post(self, request,format=None):
        filename =request.POST.get('filename',None)
        if filename:
            if os.path.isfile(filename):
                p = Popen(['md5sum', filename], stdin=PIPE, stdout=PIPE, stderr=PIPE)
                output, err = p.communicate()
                resultDir = os.path.join("/data/tmp", self.get_username(request),output.split()[0])
                #pass
            else:
                if not check_url_exist(filename):
                    raise Exception("Please Check URL or Local File Path(local files must be in /data directory) %s" % filename)
                resultDir = os.path.join("/data/tmp", self.get_username(request))
                map_read = os.path.join(resultDir,filename.split('/')[-1])
                logfile= open(resultDir + "/logfile.txt","w")
                call(['wget','-O',map_read,filename],stdout=logfile,stderr=logfile)
                logfile.close()
                p = Popen(['md5sum', map_read], stdin=PIPE, stdout=PIPE, stderr=PIPE)
                output, err = p.communicate()
                resultDir = os.path.join("/data/tmp", self.get_username(request),output.split()[0])
                filename=map_read
            try:
                os.makedirs(resultDir)
            except:
                shutil.rmtree(resultDir)
                os.makedirs(resultDir)
        else:
            raise Exception('Please provide map file filename')
        docker_cmd = self.docker_cmd % (filename,resultDir)
        result = docker_task(docker_name=self.docker_container,docker_opts=self.docker_opts,docker_command=docker_cmd,id=output.split()[0])
        logfile= glob.glob(resultDir + '/*.log')
        status = ""
        with open(logfile[0]) as f:
            data = f.read()
            if "No errors" in data:
                status="SUCCESS"
            else:
                status="FAILURE"
        return Response({
            'status':status,
            'log': data,
            'local-file': filename 
        })

def check_url_exist(url):
    p = urlparse(url)
    c = httplib.HTTPConnection(p.netloc)
    c.request("HEAD", p.path)
    return c.getresponse().status < 400
# Create your views here.
"""
class FileUploadView(APIView):

    permission_classes =(AllowAny,)
    parser_classes = (MultiPartParser, FormParser,)
    #parser_classes = (FileUploadParser,)
    renderer_classes = (JSONRenderer,)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(FileUploadView, self).dispatch(request, *args, **kwargs)

    def get_username(self, request):
        username = "guest"
        if request.user.is_authenticated():
            username = request.user.username
        return username

    def post(self, request, format=None):
    	resultDir = os.path.join("/data/tmp", self.get_username(request))
	try:
    	    os.makedirs(resultDir)
	except:
	    pass
	result={}
	for key,value in request.FILES.iteritems():
	    filename= value.name
	    local_file = "%s/%s" % (resultDir,filename)
	    self.handle_file_upload(request.FILES[key],local_file)
	    result[key]=local_file
	return Response(result)
    def handle_file_upload(self,f,filename):
	if f.multiple_chunks():
	    with open(filename, 'wb+') as temp_file:
                for chunk in f.chunks():
                    temp_file.write(chunk)
	else:
	    with open(filename, 'wb+') as temp_file:
	        temp_file.write(f.read())

"""
