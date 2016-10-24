<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:sf="http://soap.sforce.com/2006/04/metadata" xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xslt="http://xml.apache.org/xslt" xmlns:xalan="http://xml.apache.org/xalan" exclude-result-prefixes="sf">
<xsl:strip-space elements="sf:members" />
<xsl:template match="sf:types">
<xsl:for-each select="sf:members">
<xsl:value-of select="../sf:name" />::<xsl:value-of select="." /><xsl:text>&#xA;</xsl:text>
</xsl:for-each>
</xsl:template>
</xsl:stylesheet>
