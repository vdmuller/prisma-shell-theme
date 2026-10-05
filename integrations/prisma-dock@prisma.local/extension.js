// SPDX-License-Identifier: GPL-2.0-or-later
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export default class PrismaDock extends Extension {
    enable() {
        this._context = St.ThemeContext.get_for_stage(global.stage);
        this._signal = this._context.connect('changed', () => this._sync());
        this._sync();
    }
    _sync() {
        if (this._syncing) return;
        const theme = this._context.get_theme();
        const sheet = Main.getThemeStylesheet();
        const directory = sheet?.get_parent();
        let desired = null;
        try {
            const [, bytes] = directory?.get_child('prisma.json').load_contents(null) ?? [];
            const metadata = JSON.parse(new TextDecoder().decode(bytes));
            const file = directory.get_child('prisma-dock.css');
            if (metadata.project === 'Prisma' && file.query_exists(null)) desired = file;
        } catch (_error) {
            // Default and third-party themes need no Prisma overrides.
        }
        if (theme === this._theme && ((!desired && !this._file) || (desired && this._file && desired.equal(this._file)))) return;
        this._syncing = true;
        try {
            if (this._file && theme.get_custom_stylesheets().some(file => file.equal(this._file)))
                theme.unload_stylesheet(this._file);
            this._theme = theme;
            this._file = desired;
            if (desired) theme.load_stylesheet(desired);
        } finally {
            this._syncing = false;
        }
    }
    disable() {
        this._context.disconnect(this._signal);
        const theme = this._context.get_theme();
        if (this._file && theme.get_custom_stylesheets().some(file => file.equal(this._file)))
            theme.unload_stylesheet(this._file);
        this._file = null;
        this._theme = null;
        this._context = null;
    }
}
