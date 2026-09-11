const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function readCharts(name) {
    const configs = [], buttons = [0, 1].map(index => ({dataset: {series: String(index)}, closest: () => ({dataset: {chart: 'test'}}), setAttribute(key, value) {this[key] = value}, addEventListener(type, callback) {this.click = callback}}));
    const chart = {visible: true, isDatasetVisible() {return this.visible}, setDatasetVisibility(index, visible) {this.visible = visible}, update() {}};
    function Chart(element, config) {configs.push(config)}
    Chart.register = () => {}; Chart.getChart = () => chart;
    const element = {getContext: () => ({createLinearGradient: () => ({addColorStop() {}})}), addEventListener() {}};
    const context = vm.createContext({Chart, ChartDataLabels: {}, window: {innerWidth: 1200}, document: {getElementById: () => element, querySelectorAll: () => buttons, addEventListener() {}}});
    const template = fs.readFileSync(`app/templates/dashboard/${name}.html`, 'utf8');
    for (const script of template.matchAll(/<script>([\s\S]*?)<\/script>/g)) vm.runInContext(script[1].replace(/\{\{[\s\S]*?\}\}/g, '[]'), context);
    buttons[0].click(); assert.equal(chart.visible, false); assert.equal(buttons[0]['aria-pressed'], 'false');
    buttons[0].click(); assert.equal(chart.visible, true);
    return configs;
}
const overview = readCharts('overview');
for (const [name, index] of [['trend', 0], ['size', 1]]) {
    const [config] = readCharts(name);
    const serialize = value => JSON.stringify(value, (key, item) => typeof item === 'function' ? item.toString() : item);
    assert.equal(serialize(config), serialize(overview[index]), `${name} must match overview chart configuration`);
    const labels = config.options.plugins.datalabels;
    assert.equal(labels.display({dataset: {data: [0]}, dataIndex: 0}), false);
    assert.equal(labels.display({dataset: {data: [12]}, dataIndex: 0}), true);
}
console.log('Passed: trend/size configurations match overview, zero labels hidden, legends toggle.');
