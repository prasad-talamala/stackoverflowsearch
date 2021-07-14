import time
import requests
from datetime import datetime
from django.shortcuts import render
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.cache import cache


def search_questions(filters):
    stack_overflow_end = "site=stackoverflow"
    api_url = "https://api.stackexchange.com/2.3/search/advanced?{}{}".format(filters, stack_overflow_end)
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.json()['items']
    return response


def add_pagination(request, all_data):
    page = request.GET.get('page', 1)
    paginator = Paginator(all_data, 10)
    try:
        all_data = paginator.page(page)
    except PageNotAnInteger:
        all_data = paginator.page(1)
    except EmptyPage:
        all_data = paginator.page(paginator.num_pages)
    return all_data


def home(request):
    return render(request, "home.html")


def search(request):
    session = request.session.session_key

    if not session:
        session = request.session.create()

    if not request.session.get("no_of_requests_per_sessions"):
        request.session.update({"no_of_requests_per_sessions": 1})

    sess_req_incre = request.session["no_of_requests_per_sessions"]
    sess_req_incre += 1
    request.session.update({"no_of_requests_per_sessions": sess_req_incre})

    if request.session.get("no_of_requests_per_sessions") > 100:
        messages.error(request, "Maximum Search limit Exceeded. Please wait until tomorrow.")
        return render(request, "home.html")

    filter_string = ""
    for k, v in request.GET.items():
        if v and k not in ['csrfmiddlewaretoken']:
            if k in ['fromdate', 'todate', 'min', 'max']:
                timestamp = int(time.mktime(datetime.strptime(v, "%Y-%m-%d").timetuple()))
                filter_string += "{}={}&".format(k, timestamp)
            else:
                filter_string += "{}={}&".format(k, v)

    obj = cache.get(filter_string)
    if not obj:
        f = search_questions(filter_string)
        cache.set(filter_string, f)
    else:
        f = obj

    error_message = None

    if isinstance(f, list):
        final_data = add_pagination(request, f)
    else:
        final_data = []
        error_message = f.json()['error_message']
    context = {
        'data': final_data,
        'error': error_message
    }
    return render(request, "search_results.html", context=context)
