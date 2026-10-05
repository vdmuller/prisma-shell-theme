// Private GNOME 50.1 visual fixtures. SPDX-License-Identifier: GPL-2.0-or-later
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as QuickSettings from 'resource:///org/gnome/shell/ui/quickSettings.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';

const pause = ms => new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
    resolve(); return GLib.SOURCE_REMOVE;
}));

export default class PrismaQA extends Extension {
    enable() {
        const [, bytes] = GLib.file_get_contents(`${this.path}/configuration.json`);
        this.config = JSON.parse(new TextDecoder().decode(bytes));
        this.shots = [];
        this.timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 3000, () => {
            this.timer = null;
            this.run().catch(error => {
                logError(error);
                this.finish({error: `${error}\n${error.stack}`});
            });
            return GLib.SOURCE_REMOVE;
        });
    }
    disable() {
        if (this.timer) GLib.source_remove(this.timer);
    }
    finish(extra = {}) {
        GLib.file_set_contents(`${this.config.output}/result.json`, JSON.stringify({screenshots: this.shots, ...extra}, null, 2));
        global.context.terminate();
    }
    async capture(name) {
        const file = Gio.File.new_for_path(`${this.config.output}/${name}.png`);
        const stream = file.replace(null, false, Gio.FileCreateFlags.NONE, null);
        try { await new Shell.Screenshot().screenshot(false, stream); }
        finally { stream.close(null); }
        this.shots.push(name);
    }
    async checkDock() {
        const descend = actor => [actor, ...actor.get_children().flatMap(descend)];
        const container = descend(Main.uiGroup).find(actor => actor.get_name() === 'dashtodockContainer');
        if (!container) throw new Error('Ubuntu Dock was not loaded in the private session.');
        const icons = descend(container).filter(actor => actor instanceof St.Widget && actor.has_style_class_name('overview-icon'));
        if (!icons.length) throw new Error('No dock icons to validate.');
        const current = Main.getThemeStylesheet();
        Main.setThemeStylesheet(null);
        Main.loadTheme();
        if (St.ThemeContext.get_for_stage(global.stage).get_theme().get_custom_stylesheets().some(file => file.get_basename() === 'prisma-dock.css'))
            throw new Error('Prisma Dock stylesheet leaked into the default theme.');
        Main.setThemeStylesheet(current.get_path());
        Main.loadTheme();
        await pause(100);
        const states = [null, 'hover', 'active', 'checked', 'focus', 'focused', 'running'];
        for (const state of states) {
            for (const icon of icons) {
                let button = icon.get_parent();
                while (button && !(button instanceof St.Button)) button = button.get_parent();
                if (!button) continue;
                if (state === 'focused' || state === 'running') button.add_style_class_name(state);
                else if (state) button.add_style_pseudo_class(state);
                await pause(30);
                for (const actor of [button, icon]) {
                    const color = actor.get_theme_node().get_background_color();
                    const expected = state === 'hover' && actor === icon ? 30 : 0;
                    if (color.alpha !== expected)
                        throw new Error(`Unexpected dock background: ${state}, alpha=${color.alpha}, expected=${expected}`);
                }
            }
            await pause(200);
            await this.capture(`dock-${state ?? 'normal'}`);
            for (const icon of icons) {
                let button = icon.get_parent();
                while (button && !(button instanceof St.Button)) button = button.get_parent();
                if (button && (state === 'focused' || state === 'running')) button.remove_style_class_name(state);
                else if (state && button) button.remove_style_pseudo_class(state);
            }
        }
    }
    async run() {
        Main.overview.hide();
        await pause(600);
        // Real GNOME QuickSettings actors, with deterministic labels/states.
        // Headless desktops have no physical Wi-Fi, battery or brightness.
        this.fixture = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL,
            style_class: 'popup-menu-content quick-settings', x: 410, y: 120});
        const header = new St.BoxLayout({style: 'spacing: 12px;'});
        header.add_child(new St.Button({label: '96 %', style_class: 'button', x_expand: true}));
        for (const icon of ['view-refresh-symbolic', 'emblem-system-symbolic', 'changes-prevent-symbolic', 'system-shutdown-symbolic'])
            header.add_child(new St.Button({style_class: 'icon-button', child: new St.Icon({icon_name: icon, icon_size: 16})}));
        this.fixture.add_child(header);
        for (const icon of ['audio-volume-high-symbolic', 'display-brightness-symbolic']) {
            const slider = new QuickSettings.QuickSlider({icon_name: icon, icon_reactive: true,
                style: 'margin-top: 12px;'});
            slider.slider.value = .52;
            this.fixture.add_child(slider);
        }
        const rows = [
            ['Wi-Fi', 'Reference network', 'network-wireless-symbolic', true, true],
            ['Bluetooth', '', 'bluetooth-symbolic', false, true],
            ['Power mode', 'Balanced', 'power-profile-balanced-symbolic', false, true],
            ['Night Light', '', 'weather-clear-night-symbolic', false, false],
            ['Dark Style', '', 'display-brightness-symbolic', true, false],
            ['Do Not Disturb', '', 'notifications-disabled-symbolic', false, false],
            ['Keyboard', '', 'input-keyboard-symbolic', true, true],
            ['Airplane Mode', '', 'airplane-mode-symbolic', false, false],
        ];
        this.toggles = [];
        for (let i = 0; i < rows.length; i += 2) {
            const row = new St.BoxLayout({style: 'spacing: 12px; margin-top: 12px;'});
            for (const [title, subtitle, icon, checked, menu] of rows.slice(i, i + 2)) {
                const Type = menu ? QuickSettings.QuickMenuToggle : QuickSettings.QuickToggle;
                const item = new Type({title, subtitle, icon_name: icon, checked, toggle_mode: true});
                if (menu) item.menu.setHeader(icon, title, subtitle);
                row.add_child(item);
                this.toggles.push(item);
            }
            this.fixture.add_child(row);
        }
        Main.layoutManager.addChrome(this.fixture);
        for (const theme of this.config.themes) {
            Main.setThemeStylesheet(theme.css);
            Main.loadTheme();
            await pause(400);
            await this.capture(`controls-${theme.name}`);
            this.fixture.hide();
            Main.panel.statusArea.quickSettings.menu.open();
            await pause(450);
            await this.capture(`quick-settings-${theme.name}`);
            Main.panel.statusArea.quickSettings.menu.close();
            this.fixture.show();
        }
        Main.setThemeStylesheet(this.config.themes[0].css);
        Main.loadTheme();
        for (const direction of [Clutter.TextDirection.LTR, Clutter.TextDirection.RTL]) {
            this.fixture.set_text_direction(direction);
            for (const item of this.toggles) {
                item.set_text_direction(direction);
                if (item._box) {
                    item._box.set_text_direction(direction);
                    for (const child of item._box.get_children()) child.set_text_direction(direction);
                }
            }
            const id = direction === Clutter.TextDirection.RTL ? 'rtl' : 'ltr';
            // Changing an actor's direction does not invalidate St's cached
            // theme node automatically; rebuild it before checking :rtl CSS.
            const restyle = actor => {
                if (actor instanceof St.Widget) actor.style_changed();
                for (const child of actor.get_children()) restyle(child);
            };
            restyle(this.fixture);
            await pause(350);
            await this.capture(`controls-${id}`);
            for (const state of ['hover', 'focus', 'active', 'insensitive']) {
                for (const item of this.toggles) {
                    const contents = item._box?.get_first_child();
                    const button = contents instanceof St.Button ? contents : item;
                    button.add_style_pseudo_class(state);
                    if (item._menuButton) item._menuButton.add_style_pseudo_class(state);
                }
                await pause(150);
                await this.capture(`controls-${id}-${state}`);
                for (const item of this.toggles) {
                    const contents = item._box?.get_first_child();
                    const button = contents instanceof St.Button ? contents : item;
                    button.remove_style_pseudo_class(state);
                    if (item._menuButton) item._menuButton.remove_style_pseudo_class(state);
                }
            }
        }
        this.fixture.hide();
        const quick = Main.panel.statusArea.quickSettings;
        quick.menu.open();
        const network = quick._network?.quickSettingsItems.find(item => item.visible && item.hasMenu);
        if (network) {
            network.menu.open();
            await pause(500);
            await this.capture('expanded-menu');
            network.menu.close();
        }
        quick.menu.close();
        if (this.config.dock) await this.checkDock();
        Main.notify('Prisma', 'Reference notification — accent independent of backgrounds.');
        await pause(500);
        await this.capture('notification');
        Main.panel.statusArea.dateMenu.menu.open();
        await pause(450);
        const dateActors = actor => [actor, ...actor.get_children().flatMap(dateActors)];
        const headings = dateActors(Main.panel.statusArea.dateMenu.menu.actor).filter(actor =>
            actor instanceof St.Widget && (actor.has_style_class_name('calendar-day-heading') ||
                actor.has_style_class_name('calendar-month-label')));
        if (headings.length < 8) throw new Error('Calendar headings were not found.');
        for (const heading of headings) {
            if (heading.get_theme_node().get_background_color().alpha !== 0)
                throw new Error('Calendar heading has an unwanted background.');
        }
        const cards = dateActors(Main.panel.statusArea.dateMenu.menu.actor).filter(actor =>
            actor instanceof St.Widget && (actor.has_style_class_name('events-button') ||
                actor.has_style_class_name('message')));
        const eventCard = cards.find(actor => actor.has_style_class_name('events-button'));
        const notifications = cards.filter(actor => actor.has_style_class_name('message'));
        if (!eventCard || !notifications.length) throw new Error('Calendar/notification cards missing.');
        const eventColor = eventCard.get_theme_node().get_background_color();
        for (const notification of notifications) {
            const color = notification.get_theme_node().get_background_color();
            if (color.alpha !== 255 || color.red !== eventColor.red ||
                color.green !== eventColor.green || color.blue !== eventColor.blue)
                throw new Error('Notification and event surfaces differ.');
        }
        await this.capture('calendar-notifications');
        Main.panel.statusArea.dateMenu.menu.close();
        Main.messageTray._hideNotification(false);
        Main.overview.show();
        await pause(700);
        await this.capture('overview');
        Main.overview.hide();
        await pause(350);
        const dialog = new ModalDialog.ModalDialog({styleClass: 'modal-dialog'});
        dialog.contentLayout.add_child(new St.Label({text: 'Prisma — theme preview', style_class: 'dialog-title'}));
        dialog.contentLayout.add_child(new St.Label({text: 'Background and accent are configured independently.'}));
        dialog.setButtons([{label: 'Cancel', action: () => {}}, {label: 'Confirm', default: true, action: () => {}}]);
        dialog.open();
        await pause(350);
        await this.capture('dialog');
        dialog.close();
        await pause(200);
        Main.osdWindowManager.showOne(0, new Gio.ThemedIcon({name: 'audio-volume-high-symbolic'}), 'Volume', .65, 1);
        await pause(250);
        await this.capture('osd');
        this.fixture.destroy();
        this.finish({note: 'Real GNOME Shell 50.1 in a private headless session; controls fixtures use GNOME QuickToggle actors. No user theme or settings modified.'});
    }
}
