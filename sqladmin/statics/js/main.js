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

// Search
$(document).on('click','#search-button',function() {
  var searchTerm = $("#search-input").val();

  newUrl = "";
  if (window.location.search && window.location.search.indexOf('search=') != -1) {
    newUrl = window.location.search.replace( /search=[^&]*/, "search=" + searchTerm);
  } else if (window.location.search) {
    newUrl = window.location.search + "&search=" + searchTerm;
  } else {
    newUrl = window.location.search + "?search=" + searchTerm;
  }
  window.location.href = newUrl;
});

// Reset search
$(document).on('click','#search-reset',function() {
  if (window.location.search && window.location.search.indexOf('search=') != -1) {
    window.location.href = window.location.search.replace( /search=[^&]*/, "");
  }
});

// Press enter to search
$(document).on('keypress','#search-input',function(e) {
  if (e.which === 13) {
    $('#search-button').click();
  }
});
