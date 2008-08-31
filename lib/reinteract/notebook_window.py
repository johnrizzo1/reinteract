import os
import re
import sys

import gtk

from application import application
from base_window import BaseWindow
from file_list import FileList
from notebook import WorksheetFile
from window_builder import WindowBuilder
from worksheet_editor import WorksheetEditor

gtk.rc_parse_string(
    """
    style "notebook-close-button" {
       GtkWidget::focus-line-width = 0
       GtkWidget::focus-padding = 0
       GtkButton::inner-border = { 0, 0, 0, 0 }
    }
    widget "*.notebook-close-button" style : highest "notebook-close-button"
     """)

class NotebookWindow(BaseWindow):
    UI_STRING="""
<ui>
   <menubar name="TopMenu">
      <menu action="file">
         <menuitem action="new-notebook"/>
         <menuitem action="open-notebook"/>
         <menuitem action="notebook-properties"/>
         <separator/>
         <menuitem action="new-worksheet"/>
         <menuitem action="open"/>
         <menuitem action="save"/>
         <menuitem action="rename"/>
         <menuitem action="close"/>
         <separator/>
         <menuitem action="quit"/>
      </menu>
      <menu action="edit">
         <menuitem action="cut"/>
         <menuitem action="copy"/>
         <menuitem action="copy-as-doctests"/>
         <menuitem action="paste"/>
         <menuitem action="delete"/>
         <separator/>
         <menuitem action="calculate"/>
      </menu>
	<menu action="help">
        <menuitem action="about"/>
      </menu>
   </menubar>
   <toolbar name="ToolBar">
      <toolitem action="save"/>
      <separator/>
      <toolitem action="calculate"/>
   </toolbar>
</ui>
"""
    def __init__(self, notebook):
        BaseWindow.__init__(self, notebook)
        self.path = notebook.folder

        self.editors = []

        hpaned = gtk.HPaned()
        hpaned.set_position(200)
        self.main_vbox.pack_start(hpaned, expand=True, fill=True)

        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        hpaned.pack1(scrolled_window, resize=False)

        self.__file_list = FileList(self.notebook)
        scrolled_window.add(self.__file_list)
        self.__file_list.connect('open-file', self.on_file_list_open_file)

        self.__nb_widget = gtk.Notebook()
        hpaned.pack2(self.__nb_widget, resize=True)
        self.__nb_widget.connect_after('switch-page', self.on_page_switched)

        self.window.set_default_size(800, 800)

        self.main_vbox.show_all()

        self.__initial_editor = self.__new_worksheet()
        self.current_editor.view.grab_focus()

        self.__update_title()

    #######################################################
    # Overrides
    #######################################################

    def _add_actions(self, action_group):
        BaseWindow._add_actions(self, action_group)

        action_group.add_actions([
            ('notebook-properties', gtk.STOCK_PROPERTIES, "Notebook _Properties", None,         None, self.on_notebook_properties),
            ('new-worksheet',      gtk.STOCK_NEW,         "_New Worksheet",       "<control>n", None, self.on_new_worksheet),
        ])

    def _close_current(self):
        if self.current_editor:
            self.__close_editor(self.current_editor)

    def _close_window(self):
        if not self.__confirm_discard('Discard unsaved changes to worksheet "%s"?', '_Discard'):
            return

        application.window_closed(self)
        self.window.destroy()

    #######################################################
    # Utility
    #######################################################

    def __add_editor(self, editor):
        self.editors.append(editor)
        self.__nb_widget.add(editor.widget)
        editor.connect('notify::title', self.on_editor_notify_title)

        label_widget = gtk.HBox(False, 4)
        editor._notebook_tab_label = gtk.Label()
        label_widget.pack_start(editor._notebook_tab_label, True, True, 0)
        tab_button = gtk.Button()
        tab_button.set_name('notebook-close-button')
        tab_button.set_relief(gtk.RELIEF_NONE)
        tab_button.props.can_focus = False
        tab_button.connect('clicked', lambda *args: self.on_tab_close_button_clicked(editor))
        label_widget.pack_start(tab_button, False, False, 0)
        close = gtk.image_new_from_stock('gtk-close', gtk.ICON_SIZE_MENU)
        tab_button.add(close)
        label_widget.show_all()

        self.__nb_widget.set_tab_label(editor.widget, label_widget)
        self.__update_editor_title(editor)

        return editor

    def __close_editor(self, editor):
        if not editor.confirm_discard('Discard unsaved changes to worksheet "%s"?', '_Discard'):
            return

        if editor == self.current_editor:
            # Either we'll switch page and a new editor will be set, or we have no pages left
            self.current_editor = None

        if editor == self.__initial_editor:
            self.__initial_editor = None

        self.editors.remove(editor)
        editor.close()
        self.__update_title()

    def __make_editor_current(self, editor):
        self.__nb_widget.set_current_page(self.__nb_widget.page_num(editor.widget))

    def __close_initial_editor(self):
        if self.__initial_editor and not self.__initial_editor.buf.worksheet.filename and not self.__initial_editor.modified:
            self.__close_editor(self.__initial_editor)
            self.__initial_editor = None

    def __new_worksheet(self):
        editor = WorksheetEditor(self.notebook)
        self.__add_editor(editor)
        self.__make_editor_current(editor)

        return editor

    def __update_title(self, *args):
        if self.current_editor:
            title = self.current_editor.title + " - " + os.path.basename(self.notebook.folder) + " - Reinteract"
        else:
            title = os.path.basename(self.notebook.folder) + " - Reinteract"

        self.window.set_title(title)

    def __update_editor_title(self, editor):
        editor._notebook_tab_label.set_text(editor.title)
        if editor == self.current_editor:
            self.__update_title()

    def __confirm_discard(self, message_format, continue_button_text):
        for editor in self.editors:
            if editor.modified:
                # Let the user see what they are discard or not discarding
                self.window.present_with_time(gtk.get_current_event_time())
                self.__make_editor_current(editor)
                if not editor.confirm_discard(message_format, continue_button_text):
                    return False

        return True

    #######################################################
    # Callbacks
    #######################################################

    def on_notebook_properties(self, action):
        builder = WindowBuilder('notebook-properties')
        builder.dialog.set_transient_for(self.window)
        builder.dialog.set_title("%s - Properties" % self.notebook.info.name)
        builder.name_entry.set_text(self.notebook.info.name)
        builder.name_entry.set_sensitive(False)
        builder.description_text_view.get_buffer().props.text = self.notebook.info.description

        response = builder.dialog.run()
        if response == gtk.RESPONSE_OK:
            self.notebook.info.description = builder.description_text_view.get_buffer().props.text

        builder.dialog.destroy()

    def on_new_worksheet(self, action):
        self.__new_worksheet()

    def on_page_switched(self, notebook, _, page_num):
        widget = self.__nb_widget.get_nth_page(page_num)
        for editor in self.editors:
            if editor.widget == widget:
                self.current_editor = editor
                self.__update_title()
                break

    def on_editor_notify_title(self, editor, *args):
        self.__update_editor_title(editor)

    def on_tab_close_button_clicked(self, editor):
        self.__close_editor(editor)

    def on_file_list_open_file(self, file_list, file):
        self.open_file(file)

    #######################################################
    # Public API
    #######################################################

    def confirm_discard(self):
        if not self.__confirm_discard('Save the changes to worksheet "%s" before quitting?', '_Quit without saving'):
            return False

        return True

    def open_file(self, file):
        if isinstance(file, WorksheetFile):
            if file.worksheet: # Already open
                for editor in self.editors:
                    if isinstance(editor, WorksheetEditor) and editor.buf.worksheet == file.worksheet:
                        self.__make_editor_current(editor)
                        return
            else:
                editor = WorksheetEditor(self.notebook)
                editor.load(os.path.join(self.notebook.folder, file.path))
                self.__add_editor(editor)
                self.__make_editor_current(editor)

                self.__close_initial_editor()
