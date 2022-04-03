﻿namespace HasuraFunction;

using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Softozor.FusionAuth;
using Softozor.HasuraHandling.Interfaces;

public static class BuilderSetup
{
    public static void Configure(WebApplicationBuilder builder)
    {
        builder.Services.AddAutoMapper(typeof(BuilderSetup));

        builder.Services.AddFusionAuthClient();

        builder.Services.AddTransient<IActionHandler<SignUpInput, SignUpOutput>, SignUpHandler>();
    }
}