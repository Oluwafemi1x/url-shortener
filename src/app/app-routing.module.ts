import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ShortenUrlComponent } from './shorten-url.component';

const routes: Routes = [
  {path: '', redirectTo: '/shorten-url', pathMatch: 'full' },
  {path: 'shorten-url', component: ShortenUrlComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
