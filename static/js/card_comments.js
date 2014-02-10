$(function() {
	var load_form = function(url, container) {
		$.ajax(url, {
			type: 'GET',
			dataType: 'html',
			success: function(data) {
				container.html(data);
			},
			error: function(data) {
				container.html('Error getting form');
			}
		});
		return false;
	};

	var update_comments = function(card_id) {
		$.ajax('/card/'+card_id+'/comments/', {
			type: 'GET',
			dataType: 'html',
			success: function(data) {
				$('#card-comments').html(data);
			},
			error: function(data) {
				$('#card-comments').html('Error getting comments');
			}
		});
		return false;
	};

	$('#card-comment-add').on('submit','#card-comment-add-form', function() {
		$.ajax($(this).attr('action'), {
			type: 'POST',
			data: $(this).serialize(),
			dataType: 'html',
			success: function(data) {
				$('#card-comment-add').html(data);
			},
			error: function() {
				$('#card-comment-add').html('Error while submitting form');
			}
		});

		update_comments($('#card-comments').data('card-id'));

		return false;
	});

	load_form('/card/'+$('#card-comments').data('card-id')+'/comment/add/', $('#card-comment-add'));
	update_comments($('#card-comments').data('card-id'));
});