import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AppRoutingModule } from './app-routing.module';
import { RouterModule } from '@angular/router'; // Import RouterModule
import { HttpClientModule} from '@angular/common/http';

import { AppComponent } from './app.component';
import { ShortenUrlComponent } from './shorten-url.component';
import { UrlShortenerService } from './shorten-url.service';




@NgModule({
  declarations: [
    AppComponent,
    ShortenUrlComponent
    // Other components
  ],
  imports: [
    BrowserModule,
    FormsModule,
    RouterModule, // Add RouterModule here
    AppRoutingModule, // Ensure AppRoutingModule is included
    HttpClientModule
  ],
  providers: [UrlShortenerService],
  bootstrap: [AppComponent]
})
export class AppModule { }