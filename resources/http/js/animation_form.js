// this function should be called for submitting an animation form that was defined by 'animation/settings.tpl"'
function submit_animation_form(form_action) {
    // this selector and form is defined by 'animation/settings.tpl'
    let animation_selector = document.getElementById("animation_selector");
    let animation_form = document.getElementById("animation_settings_form_" + animation_selector.value);

    // add a hidden field that contains the selected animation name
    const hiddenField = document.createElement('input');
    hiddenField.type = 'hidden';
    hiddenField.name = "selected_animation_name";
    hiddenField.value = animation_selector.value;
    animation_form.appendChild(hiddenField);

    // submit the form
    animation_form.action = form_action;
    animation_form.submit();
}
