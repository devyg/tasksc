$(function() {
	$('body').on('hidden', '.modal', function () {
		$(this).removeData('modal');
	});

	var update_list = function(board_id, tasklist_id) {
		$.ajax('/tasklist/'+tasklist_id+'/cards/', {
			type: 'GET',
			dataType: 'html',
			success: function(data) {
				$('#'+tasklist_id).html(data);
			},
			error: function(data) {
				$('#'+tasklist_id).html('Error updating list');
			}
		});
		return false;
	};

	$('#newCardModal').on('submit','#addCardForm', function() {
		$.ajax($(this).attr('action'), {
			type: 'POST',
			data: $(this).serialize(),
			dataType: 'html',
			success: function(data) {
				$('#newCardModal').find('.modal-body').html(data);
			},
			error: function() {
				$('#newCardModal').find('.modal-body').html('Error while submitting form');
			}
		});

		update_list($('#addCardForm').data('board-id'), $('#addCardForm').data('tasklist-id'));

		return false;
	});
});

$(function() {
	/*$(".card-dropable").sortable({
		connectWith: ".card-dropable",
		update: function(event, ui) {
			// post request to save new card position
			//alert(ui.sender.attr('id'));
			//alert(ui.item.attr('id'));
		}
	}).disableSelection();*/
});