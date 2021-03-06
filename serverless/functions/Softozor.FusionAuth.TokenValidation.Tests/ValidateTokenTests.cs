namespace Softozor.FusionAuth.TokenValidation.Tests;

using System;
using System.Threading.Tasks;
using FluentAssertions;
using HasuraFunction;
using io.fusionauth;
using io.fusionauth.domain.api.jwt;
using io.fusionauth.jwt.domain;
using Moq;
using Softozor.HasuraHandling;
using Xunit;

public class ValidateTokenTests
{
    private const string ValidToken = "valid-token";

    private const string InvalidToken = "invalid-token";

    private readonly ValidateTokenHandler sut;

    public ValidateTokenTests()
    {
        var authClient = this.CreateFusionAuthClientStub();
        this.sut = new ValidateTokenHandler(authClient);
    }

    [Fact]
    public async Task WhenHandleValidJwtItShouldNotThrow()
    {
        // Arrange

        // Act
        Func<Task> act = async () => await this.sut.Handle(ValidToken);

        // Assert
        await act.Should().NotThrowAsync();
    }

    [Fact]
    public async Task WhenHandleInvalidJwtItShouldThrow()
    {
        // Arrange

        // Act
        Func<Task> act = async () => await this.sut.Handle(InvalidToken);

        // Assert
        var actualException = await act.Should().ThrowAsync<HasuraFunctionException>();
        actualException.Which.ErrorCode.Should().Be(401);
    }

    private IFusionAuthAsyncClient CreateFusionAuthClientStub()
    {
        var stub = new Mock<IFusionAuthAsyncClient>();

        stub.Setup(client => client.ValidateJWTAsync(It.Is<string>(token => token == ValidToken))).ReturnsAsync(new ClientResponse<ValidateResponse>
        {
            statusCode = 200, successResponse = new ValidateResponse { jwt = CreateJwt() }
        });

        stub.Setup(client => client.ValidateJWTAsync(It.Is<string>(token => token == InvalidToken))).ReturnsAsync(new ClientResponse<ValidateResponse>
        {
            statusCode = 401, exception = new Exception("the access token is invalid")
        });

        return stub.Object;
    }

    private static JWT CreateJwt()
    {
        var jwt = new JWT
        {
            aud = Guid.NewGuid().ToString(),
            exp = DateTimeOffset.FromUnixTimeSeconds(1591432060),
            iat = DateTimeOffset.FromUnixTimeSeconds(1591428460),
            iss = "company.com",
            sub = Guid.NewGuid().ToString(),
        };

        return jwt;
    }
}