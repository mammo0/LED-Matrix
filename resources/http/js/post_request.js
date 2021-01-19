// this function sends an FormData object via POST to a given url
function post_request(url, form_data_obj) {
    // create the request
    var request = new XMLHttpRequest();
    request.open("POST", url);

    // send it
    request.send(form_data_obj);
}
