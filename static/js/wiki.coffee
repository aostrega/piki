####################
#    Piki  Wiki    #
#  Copyright 2012  #
#  Artur  Ostrega  #
# ---------------- #
#  Released Under  #
#   MIT  License   #
####################

jQuery ->

  # # Constants # #
  START = 0
  END = 1
  BLOCK = 0
  CHARACTER = 1
  ENTER_KEY = 13
  BACKSPACE_KEY = 8
  SHIFT_KEY = 16
  CTRL_KEY = 17
  ALT_KEY = 18
  ESCAPE_KEY = 27
  SPACE_KEY = 32
  INVISIBLE_SPACE = '\uFEFF'
  

  # # Global Variables # #
  clickRange = {}
  oldContent = ""
  saveTimer = null
  pasting = false
  dragging = []
  

  # # Functions # #
  # initialize is the entry point of the program.
  initialize = ->
    oldContent = $('#content').clone()
    processReferences()
    bindEvents()
    window.setTimeout showHint, 10
      
  # processReferences finds references to other pages in the content as well as
  #  URLS and emails, then creates links to them. The reference to the current 
  #  page is bolded instead of linked.
  processReferences = ->
    # Unprocess references.
    $('#content').find('p .auto').contents().unwrap()
    # Compile a list of page names. 
    pages = []
    pages.push page for page in $('#index a')
    # Remember caret position.
    try
      savedSelection = rangy.getSelection().saveCharacterRanges $('#content')
    catch error
      if error.type isnt 'undefined_method'
        console.log error
    # For each page...
    paragraphs = $('#content p')
    for page in pages
      pageTitle = $(page).text()
      # and each paragraph...
      for paragraph, i in paragraphs
        # search for the page name in the paragraph.
        html = paragraph.innerHTML
        pageReference = html.toLowerCase().search pageTitle.toLowerCase()
        # If it is found...
        if pageReference isnt -1
          # make a link with it + its suffix, then move on to the next page.
          length = pageTitle.length
          while alphanumeric html[pageReference+length]
            length += 1
          beginning = html.substr 0, pageReference
          middle = html.substr pageReference, length
          if pageTitle == $('#content h1').text()
            middle = "<b class='auto'>#{middle}</b>"
          else
            location = $(page).attr 'href'
            middle = "<a class='auto' href='#{location}'>#{middle}</a>"
          end = html.substr pageReference+length
          paragraph.innerHTML = beginning+middle+end
          break
    for paragraph in paragraphs
      paragraph.innerHTML = paragraph.innerHTML.replace /\w+@\w+\.\w+/,
        "<a class='auto' href='mailto:$&'>$&</a>" # Make email links.
      paragraph.innerHTML = paragraph.innerHTML.replace /https?:\/\/\S+/,
        "<a class='auto' href='$&'>$&</a>" # Make web page links.
    # Restore caret.
    try
      rangy.getSelection().restoreCharacterRanges $('#content'), savedSelection
    catch error
      if error.type isnt 'undefined_method'
        console.log error
          
  # alphanumeric returns whether a given character string or character code is
  #  an alphanumeric character.
  alphanumeric = (character) ->
    if typeof character is 'string'
      code = character.charCodeAt()
    else
      code = character
    if (code < 48 or code > 122) or
    (code > 57 and code < 65) or
    (code > 90 and code < 97)
      false
    else
      true  

  # bindEvents binds web browser events to custom functions.
  bindEvents = ->
    $('#content').keydown keyDown
    $('#content').click showHint
    $('#content').blur -> $('#hint').hide()
    $('#save').click -> if not $(this).hasClass 'disabled' then save()
    $('#content').on 'paste', paste
    $('#pastebox').focus pasteboxFocus
    $('#index li').mousedown indexMousedown
    $('body').mouseup mouseup
    $('#settings').hover (-> $('#settingsdropdown').show()), 
      (-> 
        if $('input[name="title"]').is ':focus'
          saveSettings()
          $(this).blur() # TODO: Get this to work
        $('#settingsdropdown').hide()
        $('.expander a').next().hide()
      )
    $('.expander a').click -> $(this).next().toggle()
    $('#deletewiki a').click -> 
      $(this).addClass 'reallydelete'
      $(this).text "Really delete?"
      path = window.location.pathname.split '/'
      $(this).click -> window.location.href = "/#{path[1]}/#{path[2]}/delete!"
    $('#deletewiki a').mouseleave ->
      $(this).removeClass 'reallydelete'
      $(this).text "Delete"
      $(this).unbind 'click'
    $('input').change saveSettings
    $('#settingsdropdown form').submit -> false
    window.onbeforeunload = quit

  # indexMousedown handles mouse down events on the page index.
  indexMousedown = ->
    if $('#content').attr 'contenteditable'
      dragging = {}
      dragging.entry = this
      $(this).css 'opacity', .5
      $('#dragmarker').css 'top', 0
      $('#dragmarker').css 'left', 0
      $('#dragmarker').show()
      if $('#index li').length > 5
        mouseHandler = verticalListingMousemove
      else
        mouseHandler = horizontalListingMousemove
      $('li').mousemove {original: this}, mouseHandler
      false

  # verticalListingMousemove updates the drag marker between index listings
  #  vertically.
  verticalListingMousemove = (event) ->
    $('#index').css 'cursor', 'move'
    $('#index li a').css 'cursor', 'move'
    $('#dragmarker').css 'width', '140px'
    $('#dragmarker').css 'height', '1px'
    x = $(this).offset().left
    topY = $(this).offset().top
    middleY = $(this).offset().top + $(this).height()/2
    bottomY = $(this).offset().top + $(this).height()
    mouseY = event.pageY
    dragging.to = this
    if this is event.data.original
      $('#dragmarker').hide()
    else
      $('#dragmarker').show()
    if mouseY > topY and mouseY < middleY
      dragging.position = 'before'
      $('#dragmarker').css 'top', topY
    else
      dragging.position = 'after'
      $('#dragmarker').css 'top', bottomY
    $('#dragmarker').css 'left', x
    console.log dragging

  # horizontalListingMousemove updates the drag marker between index listings
  #  horizontally.
  horizontalListingMousemove = (event) ->
    $('#index').css 'cursor', 'move'
    $('#index li a').css 'cursor', 'move'
    $('#dragmarker').css 'width', '1px'
    $('#dragmarker').css 'height', '30px'
    $('#dragmarker').css 'margin-top', '5px'
    leftX = $(this).offset().left
    middleX = $(this).offset().left + $(this).width()/2
    rightX = $(this).offset().left + $(this).width()
    y = $(this).offset().top
    mouseX = event.pageX
    dragging.to = this
    if this is event.data.original
      $('#dragmarker').hide()
    else
      $('#dragmarker').show()
    if mouseX > leftX and mouseX < middleX
      dragging.position = 'before'
      $('#dragmarker').css 'left', leftX-12
    else
      dragging.position = 'after'
      $('#dragmarker').css 'left', rightX-12
    $('#dragmarker').css 'top', y

  # mouseup handles dropping an index listing after dragging it.
  mouseup = ->
    $(dragging.entry).css 'opacity', 1
    if dragging.to isnt dragging.entry 
      previously_preceding = $(dragging.entry).prev().text()
      switch dragging.position
        when 'before'
          $(dragging.to).before $(dragging.entry)
        when 'after'
          $(dragging.to).after $(dragging.entry)
      console.log $(dragging.entry).prev()
      path = window.location.pathname.split '/'
      $.ajax
        type: 'POST'
        url: "/#{path[1]}/#{path[2]}/update-index!"
        traditional: true
        data:
          previously_preceding: previously_preceding
          page: $(dragging.entry).text()
          new_preceding: $(dragging.entry).prev().text()
        dataType: 'text'
        success: (response) ->
          console.log response
    dragging = []
    $('#index').css 'cursor', 'default'
    $('li a').css 'cursor', 'pointer'
    $('#dragmarker').hide()
    $('li').unbind 'mousemove'

  # keyDown handles any key presses in the editor.
  # -> key press event
  keyDown = (event) ->
    key = event.which
    selection = rangy.getSelection()
    if selection.anchorNode.nodeName is '#text'
      block = selection.anchorNode.parentElement
    else
      block = selection.anchorNode
    blockType = block.tagName
    pageTitle = 'H1'
    sectionTitle = 'H2'
    subsectionTitle = 'H3'
    paragraph = 'P'
    if coordinate(START)[CHARACTER] is 0 and coordinate(END)[CHARACTER] is 0
      caretAtBlockStart = true
    else
      caretAtBlockStart = false

    # If the enter key is pressed, create a new paragraph. If the current 
    #   paragraph is empty, turn it into a section title, and into a subsection
    #   title if it's pressed again.
    if key is ENTER_KEY
      event.preventDefault()
      if blockType is pageTitle and not caretAtBlockStart
        newBlock paragraph
      else if blockType is paragraph
        if caretAtBlockStart
          newBlock sectionTitle, true
        else
          newBlock paragraph
      else if blockType is sectionTitle
        if caretAtBlockStart
          newBlock subsectionTitle, true
        else
          newBlock paragraph
      else if blockType is subsectionTitle and not caretAtBlockStart
        newBlock paragraph

    # If the backspace key is pressed, make sure it never deletes the first
    #   block of the page, and if it is an empty section/subsection title then
    #   turn it into a paragraph.
    else if key is BACKSPACE_KEY and caretAtBlockStart
      if coordinate(END)[BLOCK] is 0
        event.preventDefault()
        selection.deleteFromDocument()
      else if coordinate(END)[BLOCK] is coordinate(START)[BLOCK]
        if blockType is sectionTitle
          event.preventDefault()
          newBlock subsectionTitle, true
        else if blockType is subsectionTitle
          event.preventDefault()
          newBlock paragraph, true

    # If the escape key is pressed, disable the editor.
    # TODO: Make this work!
    else if key is ESCAPE_KEY
      event.preventDefault()
      $('#content').removeAttr 'contenteditable' 

    $('#hint').hide()

    setTimeout ->
      showHint()

      if oldContent.text() isnt $('#content').text()
        $('#save').text "Save"
        $('#save').removeClass 'disabled'
        if $('#save').hasClass 'autosave'
          clearTimeout saveTimer
          saveTimer = setTimeout save, 1000
      else
        $('#save').text "Saved"
        $('#save').addClass 'disabled'

      wikiTitle = $('#title').text()
      pageTitle = $('#content h1').text()
      if wikiTitle is pageTitle
        document.title = wikiTitle
      else if not pageTitle
        document.title = "Untitled - #{wikiTitle}"
      else
        document.title = "#{pageTitle} - #{wikiTitle}"


  # coordinate gets the coordinate of either the current selection's start or
  #   end.
  # -> START or END
  # <- [BLOCK, CHARACTER] 
  coordinate = (type) ->
    try
      selection = rangy.getSelection()
    catch error
      return [-1, -1]
    if type is START
      block = selection.anchorNode
    else
      block = selection.focusNode
    if block.nodeName is '#text'
      block = block.parentElement
    blockCoord = $('#content h1, #content h2, #content h3, #content p').index block
    if type is START
      charCoord = selection.anchorOffset
    else
      charCoord = selection.focusOffset
    [blockCoord, charCoord]
      
  # newBlock creates a new block and moves caret to it.
  # -> tag type ('P', 'H1'...), whether to replace current tag
  newBlock = (tag, replace=false) ->
    tag = tag.toLowerCase()
    selection = rangy.getSelection()
    if selection.anchorNode.nodeName is '#text'
      currentBlock = selection.anchorNode.parentElement
    else
      currentBlock = selection.anchorNode
    afterCaretRange = rangy.createRange()
    afterCaretRange.selectNodeContents currentBlock
    afterCaretRange.setStart selection.anchorNode, selection.anchorOffset
    newText = afterCaretRange.extractContents().textContent
    newText = INVISIBLE_SPACE if not newText
    $(currentBlock).after "<#{tag}>#{newText}</#{tag}>"
    newBlock_ = $(currentBlock).next()[0]
    newRange = rangy.createRange()
    newRange.selectNodeContents newBlock_
    newRange.deleteContents() if newText is INVISIBLE_SPACE
    newRange.collapse true
    selection.setSingleRange newRange
    if replace then $(currentBlock).remove()

  # showHint updates and displays the newline hint.
  showHint = ->
    selection = rangy.getSelection()
    if not selection.anchorNode? and not selection.focusNode? then return
    if selection.anchorNode.nodeName is '#text'
      block = selection.anchorNode.parentElement
    else
      block = selection.anchorNode
    if not $(block).text()
      switch block.tagName
        when 'H1' then $('#hint').text 'Page Title'
        when 'P' then $('#hint').text 'Paragraph'
        when 'H2' then $('#hint').text 'Section Title'
        when 'H3' then $('#hint').text 'Subsection Title'
      $('#hint').css 'font-size', $(block).css 'font-size'
      $('#hint').css 'line-height', $(block).css 'line-height'
      $('#hint').css 'font-weight', $(block).css 'font-weight'
      $('#hint').css 'padding-top', $(block).css 'padding-top'
      offset = $(block).offset()
      $('#hint').css 'top', offset.top
      $('#hint').css 'left', offset.left
      $('#hint').show()
    else
      $('#hint').hide()

  # save sends the page content to the server for storage.
  save = ->
    $('#save').addClass 'disabled'
    $('#save').text "Saving..."
    $('#content').find('br').remove()
    oldChildren = oldContent.children()
    cleanContent = $('#content').clone()
    cleanContent.find('p .auto').contents().unwrap()
    newChildren = cleanContent.children()
    patch = []
    blocks = Math.max(oldChildren.length, newChildren.length) - 1
    for i in [0..blocks]
      if not newChildren[i]?
        patch[i] = ""
        break
      if not oldChildren[i]? or 
      newChildren[i].innerHTML != oldChildren[i].innerHTML
        html = newChildren[i].innerHTML
        tag = newChildren[i].tagName.toLowerCase()
        patch[i] = "<#{tag}>#{html}</#{tag}>"
    path = window.location.pathname.split '/'
    path[3] = path[3] or path[2]
    $.ajax
      type: 'POST'
      url: "/#{path[1]}/#{path[2]}/#{path[3]}/save!"
      traditional: true
      data: patch: patch
      dataType: 'text'
      error: ->
        clearTimeout saveTimer
        $('#save').removeClass 'disabled'
        $('#save').text "Save"
      success: (slug) ->
        oldContent = cleanContent.clone()
        clearTimeout saveTimer
        $('#save').addClass 'disabled'
        $('#save').text "Saved"
        if slug is path[2]
          location = "/#{path[1]}/#{path[2]}"
        else
          location = "/#{path[1]}/#{path[2]}/#{slug}"
        index_entry = $("#index a[href='#{window.location.pathname}']")
        if index_entry.length
          index_entry.text $('#content h1').text()
        else
          page_title = $('#content h1').text()
          alternative_page = $("#index a:text('#{page_title}')")
          if alternative_page.length
            alternative_page.text "#{page_title} (alternative)"
            alternative_page.attr 'href', "#{alternative_page.attr 'href'}-alternative"
          $('#index ul').append "<li><a href='#{location}'>#{page_title}</a></li>"
          index_entry = $('#index a').last()
        if not $('#content h1').text()
          index_entry.remove()
        else
          index_entry.attr 'href', location
        wiki_title = $('#title').text()
        main_page_location = $('#title').attr 'href'
        if not $("#index a[href='#{main_page_location}']").length
          $('#index ul').prepend "<li><a href='#{main_page_location}'>#{wiki_title}</a></li>"
        #$('li').mousedown indexMousedown  
        if window.location.pathname != location
          window.history.replaceState "", path[2], location
        selection = rangy.saveSelection()
        processReferences()
        rangy.restoreSelection selection

  # paste is the paste event handler. It pastes clipboard text
  paste = ->
    pasting = true
    selection = rangy.saveSelection()
    node = rangy.getSelection().focusNode.parentElement
    $('#pastebox').css 'top', $(node).offset().top + $(node).height()
    $('#pastebox').focus()
    setTimeout ->
      rangy.restoreSelection selection
      document.execCommand 'insertHTML', true, $('#pastebox').val()
      $('#pastebox').val ""
      pasting = false

  # pasteboxFocus is the event handler for focusing the invisible textarea that
  #  removes formatting from clipboard text.
  pasteboxFocus = ->
    # If user is undoing and it affects the hidden paste box, undo again.
    if not pasting
      document.execCommand 'undo', false, null

  # titleUpdate updates the title based on the setting.
  titleUpdate = ->
    oldTitle = $('#title').text
    newTitle = $('input[name="title"]').val() or "Untitled"
    if document.title is oldTitle  
      document.title = newTitle
    else
      document.title = $("h1").text() + ' - ' + newTitle
    $('#title').text newTitle
    $("h1:text(oldTitle)").text newTitle
    $("#index a:text(oldTitle)").text newTitle

  # saveSettings sends settings data to the server to be saved.
  saveSettings = ->
    data =
      title: $('input[name="title"]').val() or "Untitled"
      publicity: $('input[name="publicity"]:checked').val()
      autosave: $('input[name="autosave"]:checked').val()
    if data.autosave is 'on'
      $('#save').addClass 'autosave'
    else
      $('#save').removeClass 'autosave'
    $.ajax
      type: 'POST'
      url: $('#settingsdropdown form').attr 'action'
      traditional: true
      data: data 
      dataType: 'text'
      success: (slug) ->
        if slug.slice 0, 6 is "error!"
          console.log slug
          return
        oldTitle = $('#title').text()
        newTitle = $('input[name="title"]').val() or "Untitled"
        if oldTitle != newTitle
          if document.title is oldTitle  
            document.title = newTitle
          else
            document.title = $("h1").text() + ' - ' + newTitle
          $('#title').text newTitle
          $("h1:text('#{oldTitle}')").text newTitle
          $("#index a:text('#{oldTitle}')").text newTitle
        mainPath = window.location.pathname.split '/'
        $('#title').attr 'href', "/#{mainPath[1]}/#{slug}"
        $('#settingsdropdown form').attr 'action', "/#{mainPath[1]}/#{slug}/settings!"
        $('#index a').each ->
          pagePath = $(this).attr('href').split '/'
          if pagePath[3]
            $(this).attr 'href', "/#{pagePath[1]}/#{slug}/#{pagePath[3]}"
          else
            $(this).attr 'href', "/#{pagePath[1]}/#{slug}"
        if mainPath[3]
          location = "/#{mainPath[1]}/#{slug}/#{mainPath[3]}"
        else
          location = "/#{mainPath[1]}/#{slug}"
        window.history.replaceState "", data.title, location
        processReferences()

  # quit
  quit = ->
    if $('#content[contenteditable]').length and $('#save').text() isnt "Saved"
      return "Hold on, you haven't saved yet."
    else
      return

  # An extension selector for jQuery to find by text.
  $.expr[":"].text = (obj, index, meta, stack) ->
    (obj.textContent or obj.innerText or $(obj).text() || "") is meta[3]
    
  initialize()