
$(function () {
    $('[data-toggle="tooltip"]').tooltip()
})

function input_move_path(path) {
  $('input[name=movepath]').val(path)
}

function toSub(folder) {
    var path = $('#path').val();
    var url = '';

    if (folder == '..') {
        path = path.substring(0, path.lastIndexOf('/'));
        url = '/?path=' + path;
    }
    else {
        if (path == '')
            url = '/?path=' + folder;
        else
            url = '/?path=' + path + '/' + folder;
    }

    location.href = url;
}

function folderCreate() {
    if ($('input[name=foldername]').val() != '')
        document.forms[0].submit();
}

function fileMove() {
  if ($('input[name=movepath]').val() != '')
      document.forms[2].submit();
}

$(document).on("click", ".move-file", function () {
   var myMoveFile = $(this).data('id');
   $(".modal-body #myMoveFile").val( myMoveFile );
});

// This function make ajax to get complex URL for uploading file
function fileUpload() {
    if ($('input[name=filename]').val() != '') {
        $.get('/uploadUrl', function(res) {
            var url = res;
            document.forms[1].action = url;
            document.forms[1].submit();
        });
    }
}

function delFile(fname) {
    var path = $('#path').val();
    var url = '/removefile';

    data = [path, fname]
    function redirect(url, data) {
        var form = document.createElement('form');
        document.body.appendChild(form);
        form.method = 'post';
        form.action = url;
        var input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'file';
        input.value = data;
        form.appendChild(input);
        form.submit();
      }

    redirect(url, data);
}

$('a[name=cutFile]').click(function() {
    // console.log($(this).parent().parent());
    $(this).parent().parent().hide();

});

function delFolder(folder) {
    var path = $('#path').val();
    var url = '';

    if (path == '')
      url = '/removefolder?path=' + folder;
    else
      url = '/removefolder?path=' + path + '/' + folder;

    location.href = url;
}
