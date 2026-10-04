'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
function element(){return {hidden:true,textContent:'',href:'',value:'',disabled:false,style:{},listeners:{},querySelector(){return element()},addEventListener(name,fn){this.listeners[name]=fn},append(){},appendChild(){},replaceChildren(){},setAttribute(){},select(){},remove(){},scrollIntoView(){}}}
const elements=new Map();
const timeouts=[];
const context={console,URL,URLSearchParams,AbortController,Error,document:{getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)},createElement:element,body:element(),execCommand(){return false}},navigator:{clipboard:{async writeText(){throw Error('clipboard blocked')}}},localStorage:{getItem(){return null},setItem(){throw Error('quota exceeded')},removeItem(){throw Error('storage disabled')}},window:{setTimeout(fn,ms){timeouts.push(ms);return 1},clearTimeout(){},confirm(){return true}},fetch:async()=>({ok:true,status:201,text:async()=>JSON.stringify({short_url:'https://pyc0.onrender.com/TEST1'})})};
vm.createContext(context);
vm.runInContext(fs.readFileSync('app.js','utf8'),context);
(async()=>{
 elements.get('longUrl').value='https://example.com/testing';
 elements.get('customAlias').value='';
 await elements.get('shortenForm').listeners.submit({preventDefault(){}});
 assert.equal(elements.get('resultPanel').hidden,false,'Successful shortening must show result');
 assert.equal(elements.get('formError').hidden,true,'Blocked storage must not report API failure');
 assert.equal(elements.get('shortUrl').href,'https://pyc0.onrender.com/TEST1');
 assert.equal(elements.get('shortenButton').disabled,false);
 assert.ok(timeouts.includes(60000),'Allow bounded service wake-up time');
 await vm.runInContext('copyText("https://pyc0.onrender.com/TEST1", copyButton)',context);
 assert.match(elements.get('formError').textContent,/copy it manually/);
 assert.notEqual(elements.get('copyButton').textContent,'Copied!','Failed clipboard must not claim success');
 vm.runInContext('clearHistory()',context);
 console.log('PASS: successful shortening with unavailable localStorage; bounded timeout; truthful blocked-copy fallback.');
})().catch(e=>{console.error(e);process.exitCode=1});
