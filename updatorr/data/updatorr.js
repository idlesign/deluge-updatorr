Ext.ns('Deluge.ux');

Deluge.plugins.UpdatorrPlugin = Ext.extend(Deluge.Plugin, {

	name: 'Updatorr',

	toggleLabel: {
		true: _('Enable autoupdates'),
		false: _('Disable autoupdates')
	},

	onEnable: function() {

		this.tmSep = deluge.menus.torrent.add({
			xtype: 'menuseparator'
		});
		
		this.tmToggle = deluge.menus.torrent.add({
			text: this.toggleLabel[true],
			handler: this.onToggleClick,
			scope: this
		});

		deluge.menus.torrent.on('beforeshow', this.torrentMenuToShow, this);

		this.registerTorrentStatus('Updatorr', _('Updatorr'), { colCfg: { hidden: true }});
	},

	onDisable: function() {
		deluge.menus.torrent.remove(this.tmSep);
		deluge.menus.torrent.remove(this.tmAdd);
		deluge.menus.torrent.remove(this.tmRemove);
		deluge.menus.torrent.un('beforeshow', this.torrentMenuToShow, this);
		this.deregisterTorrentStatus('Updatorr');
	},

	torrentMenuToShow: function() {
		var any = false;
		var balance = 0;

		deluge.torrents.getSelections().forEach(function(entry) {
			if (entry.data.Updatorr) { any = true; }
			balance += entry.data.Updatorr === "On" ? 1 : -1;
		});

		if (any) {
			this.tmSep.show();
			this.tmToggle.show();
			this.tmToggle.setText(this.toggleLabel[balance < 0]);
		}
		else {
			this.tmSep.hide();
			this.tmToggle.hide();
		}
	},

	onToggleClick: function(item) {
		var enable = item.text == this.toggleLabel[true];
		var ids = deluge.torrents.getSelectedIds();
		Ext.each(ids, function(id, i) {
			if (ids.length == i +1 ) {
				deluge.client.updatorr.set_items_to_update(id, enable, {
					success: function() {
						deluge.ui.update();
					}
				});
			} else {
				deluge.client.updatorr.set_items_to_update(id, enable);
			}
		});
	},

});


Deluge.registerPlugin('Updatorr', Deluge.plugins.UpdatorrPlugin);