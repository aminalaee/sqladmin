// Handle delete modal
$(document).on('shown.bs.modal', '#modal-delete', function (event) {
    var element = $(event.relatedTarget);

    var name = element.data("name");
    var pk = element.data("pk");
    $("#modal-delete-text").text("This will permanently delete " + name + " " + pk + " ?");

    $("#modal-delete-url").attr("href", element.data("url"));
});
