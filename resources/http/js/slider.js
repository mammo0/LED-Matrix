window.onload = function(){
    var slider_container = document.getElementsByClassName("slider_container");

    for(container of slider_container){
        var slider = container.getElementsByClassName("slider")[0];
        var output = container.getElementsByClassName("slider_value")[0];

        output.innerHTML = slider.value;  // Display the default slider value

        // Update the current slider value (each time you drag the slider handle)
        slider.oninput = function() {
            output.innerHTML = this.value;
        }
    }
};
