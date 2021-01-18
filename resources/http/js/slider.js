window.onload = function(){
    var slider_container = document.getElementsByClassName("slider_container");
    
    for(i in slider_container){
        var slider = slider_container[i].getElementsByClassName("slider")[0];
        var output = slider_container[i].getElementsByClassName("slider_value")[0];

        output.innerHTML = slider.value;  // Display the default slider value

        // Update the current slider value (each time you drag the slider handle)
        slider.oninput = function() {
            output.innerHTML = this.value;
        }
    }
};
 