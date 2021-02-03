window.addEventListener("load", function(){
    let slider_container = document.getElementsByClassName("slider_container");

    for(let container of slider_container){
        let slider = container.getElementsByClassName("slider")[0];
        let output = container.getElementsByClassName("slider-value")[0];

        if(output){
            output.innerHTML = slider.value;  // Display the default slider value

            // Update the current slider value (each time you drag the slider handle)
            slider.oninput = function() {
                output.innerHTML = this.value;
            }
        }
    }
});
