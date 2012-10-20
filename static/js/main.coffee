####################
#  Piki Main Page  #
#  Copyright 2012  #
#  Artur  Ostrega  #
# ---------------- #
#  Released Under  #
#   MIT  License   #
####################

jQuery ->
  switch window.location.hash
    when '#about' then $('#aboutbox').show()
    when '#log-in' 
      $('#loginbox').show()
      $('#loginbox input').first().focus()
    when '#sign-up'
      $('#signupbox').show()
      $('#signupbox input').first().focus()

  $('#menubox .piki a').click ->
    $('#aboutbox').show()
  $('#login').click ->
    $('#loginbox').show()
    $('#loginbox input').first().focus()
  $('#signup').click ->
    $('#signupbox').show()
    $('#signupbox input').first().focus()
  $('#terms').click ->
    window.open 'terms','Piki Terms', 'height=400, width=300'
  $('.back').click ->
    $(this).parent().parent().hide()
