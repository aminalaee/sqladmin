// Handle delete modal
$(document).on('shown.bs.modal', '#modal-delete', function (event) {
  var element = $(event.relatedTarget);

  var name = element.data("name");
  var pk = element.data("pk");
  $("#modal-delete-text").text("This will permanently delete " + name + " " + pk + " ?");

  $("#modal-delete-button").attr("data-url", element.data("url"));
});

$(document).on('click','#modal-delete-button',function() {
  $.ajax({
    url: $(this).attr('data-url'),
    method: 'DELETE',
    success: function(result) {
        window.location.href = result;
    }
  });
});
