// Handle delete modal
$(document).on('shown.bs.modal', '#modal-delete', function (event) {
  var element = $(event.relatedTarget);

  var name = element.data("name");
  var pk = element.data("pk");
  $("#modal-delete-text").text("This will permanently delete " + name + " " + pk + " ?");

  $("#modal-delete-button").attr("data-url", element.data("url"));
});

$(document).on('click', '#modal-delete-button', function () {
  $.ajax({
    url: $(this).attr('data-url'),
    method: 'DELETE',
    success: function (result) {
      window.location.href = result;
    }
  });
});

// Search
$(document).on('click', '#search-button', function () {
  var searchTerm = $("#search-input").val();

  newUrl = "";
  if (window.location.search && window.location.search.indexOf('search=') != -1) {
    newUrl = window.location.search.replace(/search=[^&]*/, "search=" + searchTerm);
  } else if (window.location.search) {
    newUrl = window.location.search + "&search=" + searchTerm;
  } else {
    newUrl = window.location.search + "?search=" + searchTerm;
  }
  window.location.href = newUrl;
});

// Reset search
$(document).on('click', '#search-reset', function () {
  if (window.location.search && window.location.search.indexOf('search=') != -1) {
    window.location.href = window.location.search.replace(/search=[^&]*/, "");
  }
});

// Press enter to search
$(document).on('keypress', '#search-input', function (e) {
  if (e.which === 13) {
    $('#search-button').click();
  }
});

// Date picker
$(':input[data-role="datepicker"]').each(function () {
  $(this).flatpickr({
    enableTime: false,
    allowInput: true,
    dateFormat: "Y-m-d",
  });
});

// DateTime picker
$(':input[data-role="datetimepicker"]').each(function () {
  $(this).flatpickr({
    enableTime: true,
    allowInput: true,
    enableSeconds: true,
    time_24hr: true,
    dateFormat: "Y-m-d H:i:s",
  });
});

// Time picker
$(':input[data-role="timepicker"]').each(function () {
  $(this).flatpickr({
    noCalendar: true,
    enableTime: true,
    allowInput: true,
    enableSeconds: true,
    time_24hr: true,
    dateFormat: "H:i:s",
  });
});

// Ajax Refs
$(':input[data-role="select2-ajax"]').each(function () {
  $(this).select2({
    minimumInputLength: 1,
    ajax: {
      url: $(this).data("url"),
      dataType: 'json',
      data: function (params) {
        var query = {
          name: $(this).attr("name"),
          term: params.term,
          limit: 20,
        }
        return query;
      }
    }
  });

  existing_data = $(this).data("json");
  for (var i = 0; i < existing_data.length; i++) {
    data = existing_data[i];
    var option = new Option(data.text, data.id, true, true);
    $(this).append(option).trigger('change');
  }
});
