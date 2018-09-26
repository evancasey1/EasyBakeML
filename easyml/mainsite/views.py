import pandas as pd
import numpy as np
import traceback

from .models import CsvFile, CsvFileData
from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.views import generic
from .forms import CustomUserCreationForm

# Create your views here.
def index(request):
    return HttpResponseRedirect("/easyml")

class SignUp(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'signup.html'

def upload_csv(request):
    data = {}
    if "GET" == request.method:
        return render(request, "upload_csv.html", data)

    # if not GET, then proceed
    try:
        csv_file = request.FILES["csv_file"]
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File is not CSV type')
            return HttpResponseRedirect(reverse("upload_csv"))
        # if file is too large, return
        if csv_file.multiple_chunks():
            messages.error(request, "Uploaded file is too big (%.2f MB)" % (csv_file.size / (1000 * 1000),))
            return HttpResponseRedirect(reverse("upload_csv"))

        csv_name = csv_file.name[:-4]
        user = request.user
        if CsvFile.objects.filter(raw_name=csv_file.name, file_owner=user).exists():
            csv_name = (csv_name + ' (%s)') % CsvFile.objects.filter(raw_name=csv_file.name, file_owner=user).count()

        csv_obj = CsvFile(raw_name=csv_file.name, display_name=csv_name, file_owner=user)
        csv_obj.save()

        file_data = pd.read_csv(csv_file)
        columns = list(file_data.columns.values)

        csv_data = []
        for row_index, row in file_data.iterrows():
            for i in range(len(columns)):
                header = columns[i]
                if pd.isna(row[header]):
                    continue
                data_obj = CsvFileData(parent_file=csv_obj)
                data_obj.data = row[header]
                data_obj.row_num = row_index
                data_obj.column_num = i
                data_obj.column_header = header
                csv_data.append(data_obj)

        CsvFileData.objects.bulk_create(csv_data)

    except Exception as e:
        print(traceback.format_exc(e))
        messages.error(request, "Unable to upload file. " + repr(e))

    messages.success(request, "File successfully uploaded")
    return HttpResponseRedirect("/easyml")

def manage_data(request):
    context = {}
    valid_files = CsvFile.objects.filter(file_owner=request.user)
    if not valid_files:
        valid_files = []

    context['valid_files'] = valid_files

    return render(request, 'manage_data.html', context=context)

def delete_file(request, file_id=None):
    if not file_id:
        messages.error(request, "Unable to delete file - Invalid File ID")
        return HttpResponseRedirect('manage_data.html')

    file_id = int(file_id)
    file_obj = CsvFile.objects.get(id=file_id)

    if not file_obj.file_owner == request.user:
        messages.error(request, "Unable to delete file - Invalid Permissions")
        return HttpResponseRedirect('manage_data.html')

    file_obj.delete()
    messages.success(request, "File deleted successfully")
    return HttpResponseRedirect('/easyml/manage/data')


def rename_file(request):
    file_id = request.POST.get('file_id')
    new_name = request.POST.get('display_name')

    if not (request.user == CsvFile.objects.get(id=file_id).file_owner):
        return HttpResponseRedirect('/easyml/manage/data')

    if CsvFile.objects.filter(file_owner=request.user, display_name=new_name).count() > 0:
        messages.error(request, "A file with that name already exists")
        return HttpResponseRedirect('/easyml/manage/data')

    file_obj = CsvFile.objects.get(id=file_id)
    file_obj.display_name = new_name
    file_obj.save()

    messages.success(request, "File successfully renamed")
    return HttpResponseRedirect('/easyml/manage/data')